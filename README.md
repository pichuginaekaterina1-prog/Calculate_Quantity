# Survey Cross-tab Web Interface (MVP)

Простой проект для анализа опросных таблиц (Excel) и динамического построения кросс-таблиц.

## Стек

- Backend: FastAPI + Pandas
- Frontend: простой HTML + JS
- Деплой: GitHub + Render (или любой другой хостинг)

## Как запустить локально

1. Перейти в папку backend
2. Установить зависимости:
   `pip install -r requirements.txt`
3. Запустить сервер:
   `uvicorn main:app --reload --port 8000`
4. Открыть `frontend/index.html` в браузере (или поднять статический сервер).

## API

- POST `/upload` — загрузка Excel
- GET `/questions` — список вопросов (столбцов)
- GET `/choices?question=` — значения по вопросу
- POST `/crosstab` — построить кросс-таб:
  - `row_question`, `col_question`
  - опционально `selected_row_values`, `selected_col_values`
  - `scale5` для top2/bottom2

