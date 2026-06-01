# Battle Cats Analyzer（ajuju 期末專案）

貓咪大戰爭角色分析系統：爬蟲資料、ML 模組分、全 Python 網頁（FastAPI + Jinja2）。

## 本機執行

```bash
cd battlecats_analyzer
pip install -r requirements.txt
python -m uvicorn main:app --host 127.0.0.1 --port 8000
```

瀏覽 http://127.0.0.1:8000/

## 專案結構

| 目錄 | 說明 |
|------|------|
| `battlecats_analyzer/` | Web 應用（首頁、卡池分析、搜尋、角色詳情） |
| `battle_cats_ml_test3/` | 特徵工程與隨機森林模組分 |
| `DA_ML_期末專案/` | 爬蟲 notebook 與 JSON 資料集 |
| `BattleCats_Output/` | 卡池 ID 列表 |

卡池組合分析使用 `battlecats_analyzer/data/module_scores_export.csv`。

## 部署說明

### Vercel（不建議此專案使用）

[Vercel](https://vercel.com) 主打 Node.js 與靜態站；Python 僅能跑**小型** Serverless 函式，且有：

- 部署包大小上限（含 `pandas` / `scikit-learn` 與數十 MB JSON 易超限）
- 冷啟動與執行時間限制
- 不適合啟動時載入 `battlecats_ALL_db.json`（約 56MB）這類重型資料

若堅持 Vercel，需改架構：前端靜態化 + API 精簡 + 資料放外部（S3 / Supabase），工作量較大。

### 建議：Render 或 Railway（較適合 FastAPI）

1. 將 repo 連到 [Render](https://render.com) 或 [Railway](https://railway.app)
2. 建立 **Web Service**
3. Root Directory：`battlecats_analyzer`（或依平台調整）
4. Build：`pip install -r requirements.txt`
5. Start：`uvicorn main:app --host 0.0.0.0 --port $PORT`

`render.yaml` 已提供 Render 範例設定。
