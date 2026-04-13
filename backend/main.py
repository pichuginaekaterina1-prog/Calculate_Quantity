from io import BytesIO

import pandas as pd
from fastapi import FastAPI, File, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

MULTI_MARKER = "(Множественный выбор)_"
FALSE_LIKE_VALUES = {
    "",
    "0",
    "0.0",
    "false",
    "no",
    "none",
    "nan",
    "нет",
    "не выбрано",
    "не выбран",
}

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
    "questions_meta": [],
    "question_map": {},
}


class CrosstabRequest(BaseModel):
    row_questions: list[str] | None = None
    col_questions: list[str] | None = None
    metrics: list[str] | None = None
    row_question: str | None = None
    col_question: str | None = None
    selected_row_values: list[str] | None = None
    selected_col_values: list[str] | None = None
    scale5: bool = False


@app.get("/")
def root():
    return {
        "message": "Survey Cross-tab API is running",
        "docs": "/docs",
        "health": "/health",
        "uploaded": storage["df"] is not None,
    }


@app.get("/health")
def health():
    return {
        "status": "ok",
        "uploaded": storage["df"] is not None,
    }


def normalize_value(value) -> str:
    if pd.isna(value):
        return ""
    return str(value).strip()


def is_answered_value(value) -> bool:
    return normalize_value(value) != ""


def is_selected_value(value) -> bool:
    normalized = normalize_value(value)
    return normalized != "" and normalized.lower() not in FALSE_LIKE_VALUES


def split_multi_column(column_name: str) -> tuple[str, str] | None:
    if MULTI_MARKER not in column_name:
        return None

    question_name, option_label = column_name.split(MULTI_MARKER, 1)
    question_name = question_name.strip()
    option_label = option_label.strip() or column_name.strip()
    return question_name, option_label


def ordered_unique_answers(series: pd.Series) -> list[str]:
    values = []
    seen = set()

    for value in series:
        normalized = normalize_value(value)
        if not normalized or normalized in seen:
            continue
        seen.add(normalized)
        values.append(normalized)

    return values


def build_question_catalog(df: pd.DataFrame) -> tuple[list[dict], dict[str, dict]]:
    questions = []
    question_map = {}

    for raw_column in df.columns.astype(str):
        multi_parts = split_multi_column(raw_column)

        if multi_parts:
            question_name, option_label = multi_parts
            question = question_map.get(question_name)
            if question is None:
                question = {
                    "name": question_name,
                    "kind": "multi",
                    "is_closed": True,
                    "columns": [],
                    "options": [],
                    "unique_count": 0,
                }
                questions.append(question)
                question_map[question_name] = question

            question["columns"].append(raw_column)
            question["options"].append({"label": option_label, "column": raw_column})
            question["unique_count"] = len(question["options"])
            continue

        series = df[raw_column]
        answers = ordered_unique_answers(series)
        non_blank_count = int(series.apply(is_answered_value).sum())
        unique_count = len(answers)
        unique_ratio = unique_count / non_blank_count if non_blank_count else 0

        question = {
            "name": raw_column,
            "kind": "single",
            "is_closed": non_blank_count > 0 and unique_count <= 20 and unique_ratio <= 0.5,
            "columns": [raw_column],
            "choices": answers,
            "unique_count": unique_count,
        }
        questions.append(question)
        question_map[raw_column] = question

    return questions, question_map


def get_question_definition(question_name: str) -> dict:
    question = storage["question_map"].get(question_name)
    if question is None:
        raise HTTPException(status_code=404, detail=f"Question not found: {question_name}")
    return question


def get_answered_mask(df: pd.DataFrame, question: dict) -> pd.Series:
    if question["kind"] == "single":
        return df[question["columns"][0]].apply(is_answered_value)

    mask = pd.Series(False, index=df.index)
    for option in question["options"]:
        mask = mask | df[option["column"]].apply(is_selected_value)
    return mask


def get_question_categories(df: pd.DataFrame, question: dict) -> list[dict]:
    if question["kind"] == "single":
        series = df[question["columns"][0]].apply(normalize_value)
        return [
            {"label": choice, "mask": series == choice}
            for choice in question.get("choices", [])
        ]

    return [
        {
            "label": option["label"],
            "mask": df[option["column"]].apply(is_selected_value),
        }
        for option in question["options"]
    ]


def format_metric_value(metric: str, count: int, base: int) -> float | int:
    if metric == "count":
        return int(count)
    return round((count / base * 100) if base else 0, 2)


def build_metric_table(
    df: pd.DataFrame,
    row_question: dict,
    col_question: dict,
    metric: str,
) -> dict:
    row_answered_mask = get_answered_mask(df, row_question)
    row_categories = get_question_categories(df, row_question)
    col_categories = get_question_categories(df, col_question)

    base_total = int(row_answered_mask.sum())
    columns = []

    for col_category in col_categories:
        base_mask = row_answered_mask & col_category["mask"]
        base = int(base_mask.sum())
        columns.append(
            {
                "label": col_category["label"],
                "base": base,
                "mask": base_mask,
            }
        )

    rows = []
    for row_category in row_categories:
        row_values = {}

        for column in columns:
            count = int((column["mask"] & row_category["mask"]).sum())
            row_values[column["label"]] = format_metric_value(metric, count, column["base"])

        total_count = int((row_answered_mask & row_category["mask"]).sum())
        row_values["Итого"] = format_metric_value(metric, total_count, base_total)
        rows.append({"label": row_category["label"], "values": row_values})

    bases = {column["label"]: column["base"] for column in columns}
    bases["Итого"] = base_total

    return {
        "row_question": row_question["name"],
        "col_question": col_question["name"],
        "row_kind": row_question["kind"],
        "col_kind": col_question["kind"],
        "metric": metric,
        "metric_label": "Количество (N)" if metric == "count" else "% по столбцу",
        "column_labels": [column["label"] for column in columns] + ["Итого"],
        "rows": rows,
        "bases": bases,
        "base_description": "База - фактическое количество ответивших на вопрос в каждой группе.",
    }


def resolve_crosstab_request(req: CrosstabRequest) -> tuple[pd.DataFrame, list[dict], list[dict], list[str]]:
    row_question_names = req.row_questions or ([req.row_question] if req.row_question else [])
    col_question_names = req.col_questions or ([req.col_question] if req.col_question else [])
    metrics = req.metrics or ["count", "percent"]
    metrics = [metric for metric in metrics if metric in {"count", "percent"}]

    if not row_question_names or not col_question_names:
        raise HTTPException(
            status_code=400,
            detail="At least one row question and one column question must be selected",
        )

    if not metrics:
        raise HTTPException(status_code=400, detail="At least one metric must be selected")

    df = storage["df"].copy()
    row_questions = [get_question_definition(question_name) for question_name in row_question_names]
    col_questions = [get_question_definition(question_name) for question_name in col_question_names]

    return df, row_questions, col_questions, metrics


def build_tables_for_request(req: CrosstabRequest) -> dict:
    df, row_questions, col_questions, metrics = resolve_crosstab_request(req)

    tables = [
        build_metric_table(df, row_question, col_question, metric)
        for row_question in row_questions
        for col_question in col_questions
        for metric in metrics
    ]

    return {
        "tables": tables,
        "row_questions": [question["name"] for question in row_questions],
        "col_questions": [question["name"] for question in col_questions],
        "metrics": metrics,
    }


def append_table_to_sheet_rows(sheet_rows: list[list], table: dict):
    sheet_rows.append([f'{table["row_question"]} x {table["col_question"]}'])
    sheet_rows.append([table["metric_label"]])
    sheet_rows.append(["Варианты ответа", *table["column_labels"]])

    for row in table["rows"]:
        sheet_rows.append(
            [row["label"], *[row["values"].get(column_label, 0) for column_label in table["column_labels"]]]
        )

    sheet_rows.append(["База", *[table["bases"].get(column_label, 0) for column_label in table["column_labels"]]])
    sheet_rows.append([table["base_description"]])
    sheet_rows.append([])


def build_export_workbook(tables: list[dict]) -> BytesIO:
    output = BytesIO()
    metric_to_sheet = {
        "count": "Количество (N)",
        "percent": "% по столбцу",
    }

    with pd.ExcelWriter(output, engine="openpyxl") as writer:
        for metric, sheet_name in metric_to_sheet.items():
            metric_tables = [table for table in tables if table["metric"] == metric]
            if not metric_tables:
                continue

            sheet_rows = []
            for table in metric_tables:
                append_table_to_sheet_rows(sheet_rows, table)

            pd.DataFrame(sheet_rows).to_excel(
                writer,
                sheet_name=sheet_name,
                index=False,
                header=False,
            )

    output.seek(0)
    return output


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
    except Exception as exc:
        raise HTTPException(status_code=400, detail=f"Failed to read Excel: {exc}")

    if df.empty:
        raise HTTPException(status_code=400, detail="Empty Excel file")

    questions_meta, question_map = build_question_catalog(df)

    storage["df"] = df
    storage["columns"] = df.columns.astype(str).tolist()
    storage["questions_meta"] = questions_meta
    storage["question_map"] = question_map

    return {
        "rows": len(df),
        "columns": storage["columns"],
        "questions": [question["name"] for question in questions_meta],
    }


@app.get("/questions")
def questions():
    if storage["df"] is None:
        raise HTTPException(status_code=404, detail="No data uploaded")

    return {
        "questions": [question["name"] for question in storage["questions_meta"]],
        "items": storage["questions_meta"],
    }


@app.get("/choices")
def choices(question: str):
    if storage["df"] is None:
        raise HTTPException(status_code=404, detail="No data uploaded")

    question_def = get_question_definition(question)

    if question_def["kind"] == "single":
        return {"question": question, "choices": question_def.get("choices", [])}

    return {
        "question": question,
        "choices": [option["label"] for option in question_def.get("options", [])],
    }


@app.post("/crosstab")
def crosstab(req: CrosstabRequest):
    if storage["df"] is None:
        raise HTTPException(status_code=404, detail="No data uploaded")

    return build_tables_for_request(req)


@app.post("/export/xlsx")
def export_xlsx(req: CrosstabRequest):
    if storage["df"] is None:
        raise HTTPException(status_code=404, detail="No data uploaded")

    result = build_tables_for_request(req)
    workbook = build_export_workbook(result["tables"])

    return StreamingResponse(
        workbook,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={
            "Content-Disposition": 'attachment; filename="crosstab_export.xlsx"',
        },
    )
