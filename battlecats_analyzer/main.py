"""Battle Cats Analyzer — FastAPI web app (Python only, no separate JS)."""

import urllib.error
import urllib.request
from pathlib import Path

from fastapi import FastAPI, Form, HTTPException, Query, Request
from fastapi.responses import HTMLResponse, Response
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from config import APP_TITLE, POOL_NAME, unit_image_url
from services.catalog import (
    get_carousel_slides,
    get_character_detail,
    get_gacha_pool,
    search_characters,
)
from services.roster_analysis import analyze_roster

APP_DIR = Path(__file__).resolve().parent
app = FastAPI(title=APP_TITLE)
app.mount("/static", StaticFiles(directory=APP_DIR / "static"), name="static")
templates = Jinja2Templates(directory=APP_DIR / "templates")


@app.on_event("startup")
def preload_data():
    from services.catalog import get_catalog

    get_catalog()


_IMAGE_CACHE: dict[str, bytes] = {}


@app.get("/image/{cat_id}")
async def proxy_unit_image(cat_id: str):
    cid = str(cat_id).zfill(3)
    if cid in _IMAGE_CACHE:
        return Response(content=_IMAGE_CACHE[cid], media_type="image/png")

    upstream = unit_image_url(cid, local=False)
    req = urllib.request.Request(upstream, headers={"User-Agent": "Mozilla/5.0"})
    try:
        with urllib.request.urlopen(req, timeout=12) as resp:
            data = resp.read()
    except urllib.error.URLError as exc:
        raise HTTPException(status_code=404, detail="image not found") from exc

    if len(data) < 200 or data[:4] != b"\x89PNG":
        raise HTTPException(status_code=404, detail="invalid image")

    _IMAGE_CACHE[cid] = data
    return Response(content=data, media_type="image/png")


@app.get("/", response_class=HTMLResponse)
async def home(request: Request):
    return templates.TemplateResponse(
        request,
        "index.html",
        {
            "title": APP_TITLE,
            "slides": get_carousel_slides(),
            "pool_name": POOL_NAME,
        },
    )


def _gacha_context(query: str, selected_ids: list[str], analysis=None):
    selected = {str(i).zfill(3) for i in selected_ids}
    return {
        "title": APP_TITLE,
        "pool_name": POOL_NAME,
        "query": query,
        "characters": get_gacha_pool(query),
        "selected_ids": selected,
        "analysis": analysis,
    }


@app.get("/gacha", response_class=HTMLResponse)
async def gacha_page(
    request: Request,
    q: str = Query("", alias="q"),
    select_all: bool = Query(False),
):
    chars = get_gacha_pool(q)
    selected = [c["id"] for c in chars] if select_all else []
    return templates.TemplateResponse(
        request,
        "gacha.html",
        _gacha_context(q, selected),
    )


@app.post("/gacha", response_class=HTMLResponse)
async def gacha_analyze(
    request: Request,
    q: str = Form(""),
    selected_ids: list[str] = Form([]),
):
    analysis = analyze_roster(selected_ids)
    return templates.TemplateResponse(
        request,
        "gacha.html",
        _gacha_context(q, selected_ids, analysis=analysis),
    )


@app.get("/search", response_class=HTMLResponse)
async def search_page(request: Request, q: str = Query("", alias="q")):
    return templates.TemplateResponse(
        request,
        "search.html",
        {
            "title": APP_TITLE,
            "query": q,
            "characters": search_characters(q),
        },
    )


@app.get("/character/{cat_id}", response_class=HTMLResponse)
async def character_page(request: Request, cat_id: str):
    detail = get_character_detail(cat_id)
    if not detail:
        return templates.TemplateResponse(
            request,
            "not_found.html",
            {"title": APP_TITLE, "cat_id": cat_id},
            status_code=404,
        )
    return templates.TemplateResponse(
        request,
        "detail.html",
        {"title": APP_TITLE, "c": detail},
    )


if __name__ == "__main__":
    import uvicorn

    uvicorn.run("main:app", host="127.0.0.1", port=8000, reload=False)
