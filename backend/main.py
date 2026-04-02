from fastapi import FastAPI, File, UploadFile, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from io import BytesIO
import pandas as pd

app = FastAPI(title="Survey Cross-tab API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

storage = {
    "df": None,
    "columns": [],
}

class CrosstabRequest(BaseModel):
    row_question: str
    col_question: str
    selected_row_values: list[str] | None = None
    selected_col_values: list[str] | None = None
    scale5: bool = False


@app.post("/upload")
async def upload_excel(file: UploadFile = File(...)):
    if file.content_type not in [
        "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        "application/vnd.ms-excel",
        "application/octet-stream",
    ]:
        raise HTTPException(status_code=400, detail="Unsupported file type")

    content = await file.read()
    try:
        df = pd.read_excel(BytesIO(content))
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Failed to read Excel: {e}")

    if df.empty:
        raise HTTPException(status_code=400, detail="Empty Excel file")

    storage["df"] = df
    storage["columns"] = df.columns.astype(str).tolist()

    return {
        "rows": len(df),
        "columns": storage["columns"],
    }


@app.get("/questions")
def questions():
    if storage["df"] is None:
        raise HTTPException(status_code=404, detail="No data uploaded")
    return {"questions": storage["columns"]}


@app.get("/choices")
def choices(question: str):
    if storage["df"] is None:
        raise HTTPException(status_code=404, detail="No data uploaded")
    if question not in storage["columns"]:
        raise HTTPException(status_code=404, detail="Question not found")

    values = storage["df"][question].dropna().astype(str).unique().tolist()
    values.sort()
    return {"question": question, "choices": values}


@app.post("/crosstab")
def crosstab(req: CrosstabRequest):
    if storage["df"] is None:
        raise HTTPException(status_code=404, detail="No data uploaded")

    df = storage["df"].copy()

    if req.row_question not in storage["columns"] or req.col_question not in storage["columns"]:
        raise HTTPException(status_code=404, detail="Question not found")

    if req.selected_row_values is not None:
        df = df[df[req.row_question].astype(str).isin(req.selected_row_values)]

    if req.selected_col_values is not None:
        df = df[df[req.col_question].astype(str).isin(req.selected_col_values)]

    row_respondents = df[req.row_question].notna().sum()
    col_respondents = df[req.col_question].notna().sum()

    ct = pd.crosstab(df[req.row_question], df[req.col_question], dropna=False)
    pct = ct.div(ct.sum(axis=1).replace(0, 1), axis=0) * 100

    result = {
        "row_question": req.row_question,
        "col_question": req.col_question,
        "row_respondents": int(row_respondents),
        "col_respondents": int(col_respondents),
        "crosstab": ct.fillna(0).astype(int).to_dict(),
        "percent": pct.round(2).fillna(0).to_dict(),
    }

    if req.scale5:
        def agg_scale(q):
            s = pd.to_numeric(df[q], errors='coerce')
            total = s.notna().sum() or 1
            top2 = s[s >= 4].count() / total * 100
            bottom2 = s[s <= 2].count() / total * 100
            return {
                "total_respondents": int(total),
                "top2_percent": round(float(top2), 2),
                "bottom2_percent": round(float(bottom2), 2),
            }

        result["scale5"] = {
            "row_question": agg_scale(req.row_question),
            "col_question": agg_scale(req.col_question),
        }

    return result
