"""Battle Cats Analyzer — FastAPI web app (Python only, no separate JS)."""

import urllib.error
import urllib.request
from pathlib import Path

from fastapi import FastAPI, Form, HTTPException, Query, Request
from fastapi.responses import HTMLResponse, Response
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from starlette.middleware.sessions import SessionMiddleware

from config import (
    APP_TITLE,
    POOL_NAME,
    SESSION_COOKIE_NAME,
    SESSION_KEY_OWNED,
    SESSION_MAX_AGE,
    SESSION_SECRET,
    unit_image_url,
)
from services.catalog import (
    get_carousel_slides,
    get_character_detail,
    get_gacha_pool,
    search_characters,
)
from services.roster_analysis import analyze_roster

APP_DIR = Path(__file__).resolve().parent
app = FastAPI(title=APP_TITLE)
app.add_middleware(
    SessionMiddleware,
    secret_key=SESSION_SECRET,
    session_cookie=SESSION_COOKIE_NAME,
    max_age=SESSION_MAX_AGE,
    same_site="lax",
    https_only=False,
)
app.mount("/static", StaticFiles(directory=APP_DIR / "static"), name="static")
templates = Jinja2Templates(directory=APP_DIR / "templates")


@app.on_event("startup")
def preload_data():
    """Warm cache in background; app still starts if ML stack is slow."""
    import logging

    try:
        from services.catalog import get_catalog

        get_catalog()
        logging.getLogger("uvicorn.error").info("Catalog preloaded.")
    except Exception as exc:
        logging.getLogger("uvicorn.error").warning(
            "Catalog preload skipped (will lazy-load): %s", exc
        )


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


def _normalize_cat_ids(ids: list[str]) -> list[str]:
    return sorted({str(i).strip().zfill(3) for i in ids if str(i).strip()})


def _load_owned_session(request: Request) -> list[str]:
    raw = request.session.get(SESSION_KEY_OWNED, [])
    if isinstance(raw, list):
        return _normalize_cat_ids([str(x) for x in raw])
    return []


def _save_owned_session(request: Request, ids: list[str]) -> list[str]:
    normalized = _normalize_cat_ids(ids)
    request.session[SESSION_KEY_OWNED] = normalized
    return normalized


def _gacha_context(
    query: str,
    selected_ids: list[str],
    *,
    analysis=None,
    saved_message: str | None = None,
):
    selected = {str(i).zfill(3) for i in selected_ids}
    return {
        "title": APP_TITLE,
        "pool_name": POOL_NAME,
        "query": query,
        "characters": get_gacha_pool(query),
        "selected_ids": selected,
        "owned_count": len(selected),
        "analysis": analysis,
        "saved_message": saved_message,
    }


@app.get("/gacha", response_class=HTMLResponse)
async def gacha_page(
    request: Request,
    q: str = Query("", alias="q"),
    select_all: bool = Query(False),
    clear_owned: bool = Query(False),
):
    if clear_owned:
        request.session.pop(SESSION_KEY_OWNED, None)
        selected: list[str] = []
    elif select_all:
        chars = get_gacha_pool(q)
        selected = _save_owned_session(request, [c["id"] for c in chars])
    else:
        selected = _load_owned_session(request)

    return templates.TemplateResponse(
        request,
        "gacha.html",
        _gacha_context(q, selected),
    )


@app.post("/gacha", response_class=HTMLResponse)
async def gacha_post(
    request: Request,
    q: str = Form(""),
    selected_ids: list[str] = Form([]),
    action: str = Form("analyze"),
):
    saved = _save_owned_session(request, selected_ids)
    analysis = None
    saved_message = None

    if action == "save":
        saved_message = f"已儲存 {len(saved)} 隻持有角色（離開頁面後仍會保留勾選）"
    else:
        analysis = analyze_roster(saved)
        saved_message = f"已儲存 {len(saved)} 隻持有角色並完成組合分析"

    return templates.TemplateResponse(
        request,
        "gacha.html",
        _gacha_context(q, saved, analysis=analysis, saved_message=saved_message),
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
