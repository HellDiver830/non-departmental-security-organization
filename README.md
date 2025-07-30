# Sci‑Fi Security HUD

Прототип СУБД для вневедомственной охранной службы из научно‑фантастических фильмов

## Описание

Backend на Python + Eel с локальной SQLite‑базой, AI‑ассистентом Google Gemini и оффлайн‑распознаванием речи через Vosk.
Frontend — HTML/JS в папке `web/`, реализующий:

* Таблицы редактируемых данных (Сотрудники, Объекты, Расходы)
* 3D‑глобус с метками (three‑globe + Tippy.js)
* Чат‑окно и голосовой ввод (Web Speech API и Vosk)

## Структура репозитория

```
.
├─ main.py                        # Backend: Eel + SQLite + Gemini + Vosk
├─ security.db                   # Готовая база SQLite с демо-данными
├─ security.accdb                # Та же БД в формате MS Access
├─ vosk-model-small-ru-0.4.zip   # Модель Vosk для оффлайн-распознавания речи (русский)
└─ web/                          # Фронтенд для Eel
   ├─ index.html                 # UI (таблицы, чат, глобус)
   └─ script.js                  # Логика: заполнение таблиц, глобус, чат
```

## Функции

* **Хранение** и **просмотр** информации о сотрудниках, объектах и расходах
* **Редактирование in‑place** в HTML‑таблицах с автосохранением
* **3D‑глобус** с разными цветами для сотрудников и объектов
* **Чат‑ассистент** на базе модели **Gemini 2.0 Flash**

  * Поддерживает JSON‑команды для CRUD‑операций над БД
  * Примеры команд:

    ```json
    {"action":"get_incidents","object_id":3}
    {"action":"update_health","employee_id":7,"new_class":"C"}
    ```
* **Голосовой ввод и распознавание речи**:

  * В браузере через Web Speech API
  * Оффлайн через Vosk с моделью `vosk-model-small-ru-0.4.zip` (см. раздел Структура)

## Установка

1. Клонировать репозиторий:

   ```bash
   git clone https://github.com/HellDiver830/non-departmental-security-organization.git
   cd non-departmental-security-organization
   ```
2. Создать и активировать виртуальное окружение (рекомендуется):

   ```bash
   python -m venv venv
   source venv/bin/activate   # Linux/macOS
   venv\\Scripts\\activate  # Windows
   ```
3. Установить зависимости:

   ```bash
   pip install eel google-generativeai pyttsx3 vosk
   ```
4. Модель Vosk не включена в репозиторий. Необходимо скачать её напрямую и добавить по схеме выше:

   ```
   https://alphacephei.com/vosk/models/vosk-model-small-ru-0.22.zip
   ```
5. Задать API‑ключ для Gemini вместо хардкода в `main.py`:

   ```bash
   export GEMINI_KEY="ваш_ключ_Gemini"
   ```

## Запуск

```bash
python main.py
```

Откроется окно с UI: таблицы, глобус, чат‑ассистент и голосовой ввод.

## Лицензия

MIT License
