# Survey Cross-tab Web Interface

Веб-приложение для анализа результатов опросов (Excel) с динамическим построением кросс-таблиц, фильтрацией и специальной обработкой 5-балльных шкал.

**Особенности:**
- 📊 Загрузка Excel с ответами респондентов
- 🔀 Построение кросс-табов "вопрос × вопрос" 
- 📈 Расчёт процентов от ответивших (N и %)
- ⭐ Для 5-балльных шкал: top-2 (4-5) и bottom-2 (1-2)
- 🎯 Фильтрация по выбранным ответам
- 🚀 Готов к деплою на Render

---

## 🏗 Архитектура

```
survey-cross-tab/
├── backend/
│   ├── main.py          # FastAPI приложение
│   └── requirements.txt  # Python зависимости
├── frontend/
│   └── index.html       # Веб-интерфейс (HTML + JS)
├── пример базы.xlsx     # Пример данных
├── README.md
├── .gitignore
└── render.yaml          # Конфиг для Render
```

---

## 🛠 Стек

- **Backend:** FastAPI + Pandas + Uvicorn
- **Frontend:** HTML5 + Vanilla JavaScript
- **Данные:** Excel (.xlsx)
- **Деплой:** Docker (Render) + GitHub

---

## 📋 Требования

- Python 3.9+
- pip или conda
- Git
- Аккаунт на GitHub + Render (для деплоя)

---

## 🚀 Запуск локально

### 1. Клонировать репозиторий

```bash
git clone https://github.com/<ваше_имя>/<имя_репо>.git
cd survey-cross-tab
```

### 2. Установить зависимости

```bash
cd backend
pip install -r requirements.txt
cd ..
```

### 3. Запустить backend

```bash
uvicorn backend.main:app --reload --port 8000
```

Сервер будет доступен на `http://127.0.0.1:8000`

### 4. Открыть frontend

Откройте файл `frontend/index.html` прямо в браузере (или используйте расширение Live Server в VS Code).

### 5. Использовать приложение

1. Нажмите **"Загрузить"** и выберите файл Excel
2. Выберите вопрос для строк и столбцов
3. (опционально) отметьте галочку **"5-балльная..."** для top2/bottom2
4. Нажмите **"Считать кросс-таб"**

---

## 📊 Формат входных данных (Excel)

Ожидаемая структура:
- **В строках:** каждый респондент (одна строка = один ответ)
- **В столбцах:** вопросы опроса
- **В ячейках:** ответы (текст, числа, или пусто для "не ответил")

### Пример:

| Вопрос1 | Вопрос2 | Вопрос3 (5-балл) | ... |
|---------|---------|------------------|-----|
| Да      | 25-35   | 5                | ... |
| Нет     | 18-24   | 3                | ... |
| Нет     | 35-50   | 4                | ... |

---

## 🔌 REST API

### `POST /upload`
Загрузить Excel файл

**Request:**
```
Content-Type: multipart/form-data
file: <Excel file>
```

**Response:**
```json
{
  "rows": 250,
  "columns": ["Q1", "Q2", "Q3_scale", "Q4", ...]
}
```

---

### `GET /questions`
Получить список всех вопросов

**Response:**
```json
{
  "questions": ["Q1", "Q2", "Q3_scale", "Q4"]
}
```

---

### `GET /choices?question=Q1`
Получить варианты ответов для вопроса

**Response:**
```json
{
  "question": "Q1",
  "choices": ["Да", "Нет", "Затрудняюсь ответить"]
}
```

---

### `POST /crosstab`
Построить кросс-таблицу

**Request:**
```json
{
  "row_question": "Q1",
  "col_question": "Q3_scale",
  "selected_row_values": null,
  "selected_col_values": null,
  "scale5": true
}
```

**Response:**
```json
{
  "row_question": "Q1",
  "col_question": "Q3_scale",
  "row_respondents": 235,
  "col_respondents": 240,
  "crosstab": {
    "Да": {"1": 5, "2": 10, "3": 45, "4": 50, "5": 60},
    "Нет": {"1": 15, "2": 20, "3": 40, "4": 30, "5": 20}
  },
  "percent": {
    "Да": {"1": 2.13, "2": 4.26, "3": 19.15, "4": 21.28, "5": 25.53},
    "Нет": {"1": 10.99, "2": 14.63, "3": 29.20, "4": 21.90, "5": 14.60}
  },
  "scale5": {
    "row_question": {
      "total_respondents": 235,
      "top2_percent": 46.81,
      "bottom2_percent": 5.21
    },
    "col_question": {
      "total_respondents": 240,
      "top2_percent": 71.25,
      "bottom2_percent": 8.75
    }
  }
}
```

---

## 🌐 Деплой на Render

### 1. Создать GitHub репозиторий

```bash
git init
git add .
git commit -m "Init survey cross-tab MVP"
git branch -M main
git remote add origin https://github.com/<yourusername>/<repo>.git
git push -u origin main
```

### 2. Подключить Render

1. Перейти на [https://render.com](https://render.com)
2. Sign up / Log in
3. Нажать **New** → **Web Service**
4. Выбрать GitHub репозиторий
5. Заполнить:
   - **Name:** `survey-cross-tab`
   - **Environment:** `Python 3`
   - **Build Command:** `pip install -r backend/requirements.txt`
   - **Start Command:** `uvicorn backend.main:app --host 0.0.0.0 --port 10000`
6. Нажать **Create Web Service**

Render автоматически развернёт приложение. У вас появится URL вида `https://survey-cross-tab-xxx.onrender.com`

### 3. Обновить frontend для production

Отредактируйте строку в `frontend/index.html`:

```javascript
// Перед деплоем:
const apiUrl = "http://127.0.0.1:8000";

// После деплоя (замените на ваш URL Render):
const apiUrl = "https://survey-cross-tab-xxx.onrender.com";
```

Затем:
```bash
git add frontend/index.html
git commit -m "Update API URL for production"
git push
```

Render автоматически перезагрузит приложение.

---

## 🧪 Тестирование

### Локально

```bash
# Terminal 1: Backend
uvicorn backend.main:app --reload --port 8000

# Terminal 2: Откройте frontend/index.html в браузере
```

### На Render

1. Откройте ваш URL Render: `https://survey-cross-tab-xxx.onrender.com`
2. Откройте DevTools (F12) и проверьте консоль на ошибки
3. Загрузите пример данных (`пример базы.xlsx`)
4. Выберите вопросы и постройте кросс-таб

---

## 🐛 Troubleshooting

### "No data uploaded"
- Убедитесь, что вы загрузили Excel файл
- Проверьте, что файл не пуст

### CORS ошибка (при production)
- Если frontend и backend на разных доменах, нужно обновить `apiUrl` в `frontend/index.html`
- Backend уже настроен на CORS (`allow_origins=["*"]`)

### Render говорит "Build failed"
- Проверьте, что `backend/requirements.txt` содержит все зависимости
- Убедитесь, что `render.yaml` правилен
- Посмотрите логи в Render dashboard

### Excel не загружается
- Проверьте, что используется формат `.xlsx` (не `.xls`)
- Убедитесь, что в файле нет проблемных спецсимволов

---

## 📝 Возможные расширения

- [ ] Система аутентификации (OAuth, JWT)
- [ ] Сохранение результатов в БД (PostgreSQL, SQLite)
- [ ] Многоязычный интерфейс
- [ ] Экспорт результатов (PDF, CSV, Excel)
- [ ] Мультиселект для фильтрации ответов
- [ ] Поддержка больших файлов (>100k rows) через streaming
- [ ] Улучшенный UI (React, Tailwind CSS)
- [ ] Дополнительные статистики (медиана, стд. отклонение)

---

## 📄 Лицензия

MIT License — используйте свободно.

---

## 💬 Контакты

Вопросы или предложения? Откройте Issue на GitHub.

---

**Создано:** апрель 2026
**Версия:** 1.0.0 (MVP)

