"""
Sci-Fi Security HUD · backend           (main.py  v1.2)
────────────────────────────────────────────────────────
• База     : SQLite  (security.db)
• Фронт    : Eel  (папка web/  — index.html + script.js)
• Ассистент: Gemini ― обычный чат + JSON-команды
             (Flash/Pro через system_instruction).
"""

import os, re, json, sqlite3
from threading import Thread
import inspect, traceback   #  ← добавьте к import-ам в начале файла
import eel
import google.generativeai as genai
import pyttsx3                       # ← пока не используем, но оставили

# ──────────────────── CONFIG ────────────────────
DB_FILE      = "security.db"
GEMINI_KEY   = "AIzaSyBMSPDEtJYmwWIx13Lfck5yuq1rvFORV_g"           # ваш ключ
GEMINI_MODEL = os.getenv("GEMINI_MODEL", "gemini-2.0-flash")

if not GEMINI_KEY:
    print("⚠️  GEMINI_API_KEY не задан — ассистент будет «немой».")
    model = None
else:
    genai.configure(api_key=GEMINI_KEY)
    model = genai.GenerativeModel(GEMINI_MODEL)

# ──────────────────── DATABASE ────────────────────
conn = sqlite3.connect(DB_FILE, check_same_thread=False)
conn.row_factory = sqlite3.Row
cur = conn.cursor()

cur.executescript("""
CREATE TABLE IF NOT EXISTS Employees(
    ID INTEGER PRIMARY KEY,
    FullName TEXT, BirthDate TEXT, HealthClass TEXT,
    Role TEXT, Equipment TEXT, PatrolHistory TEXT, Warnings INTEGER
);
CREATE TABLE IF NOT EXISTS Objects(
    ID INTEGER PRIMARY KEY,
    ObjName TEXT, Lat REAL, Lng REAL,
    Criticality TEXT, IncidentHistory TEXT, Rating INTEGER
);
CREATE TABLE IF NOT EXISTS Expenses(
    ID INTEGER PRIMARY KEY,
    Date TEXT, Item TEXT, Quantity INTEGER,
    Cost INTEGER, AssignedTo INTEGER
);
""")
conn.commit()

# ─── seed demo data (10 строк) ───
def seed():
    if conn.execute("SELECT COUNT(*) FROM Employees").fetchone()[0]:
        return
    roles  = ["Guard","Dispatcher","Technician","Supervisor"]
    equips = ["Radio,Baton","Handcuffs,Radio","Flashlight,Kit","Pistol,Radio"]
    for i in range(1,11):
        conn.execute("""INSERT INTO Employees
            (FullName,BirthDate,HealthClass,Role,Equipment,PatrolHistory,Warnings)
            VALUES(?,?,?,?,?,?,0)""",
            (f"Employee {i}", f"19{70+i}-01-01", "ABC"[i%3],
             roles[i%4], equips[i%4],
             f"2025-05-0{i}: Patrol sector {i}"))
    levels=["Low","Medium","High"]
    for i in range(1,11):
        lat = round((i*7)%90  -45 + i*0.4, 4)
        lng = round((i*17)%180 -90 + i*1.3, 4)
        conn.execute("""INSERT INTO Objects
            (ObjName,Lat,Lng,Criticality,IncidentHistory,Rating)
            VALUES(?,?,?,?,?,?)""",
            (f"Object {i}", lat, lng, levels[i%3],
             f"2024-0{i}-15 incident; 2025-0{i}-22 false alarm",
             (i%5)+1))
    items=["Uniform","Fuel","Batteries","Flashlight","First Aid"]
    for i in range(1,11):
        conn.execute("""INSERT INTO Expenses
            (Date,Item,Quantity,Cost,AssignedTo)
            VALUES(?,?,?,?,?)""",
            (f"2025-05-{i:02}", items[i%5], (i%3)+1, 20+i*5,
             i if i%2==0 else None))
    conn.commit()
seed()

# ──────────────────── GEMINI PROMPT ────────────────────
SYSTEM_PROMPT = (
    "Ты — ассистент диспетчера охранной службы.\n"
    "Если пользователь просит получить или изменить данные БД, "
    "верни ТОЛЬКО JSON одной строкой с ключом action.\n"
    "Поддерживаемые action:\n"
    "  get_incidents  {object_id:int}\n"
    "  get_patrols    {employee_id:int}\n"
    "  update_health  {employee_id:int,new_class:str(A|B|C)}\n"
    "Иначе — дай обычный разговорный ответ.\n"
    "Примеры:\n"
    "  «покажи историю инцидентов объекта 3» → "
    "{\"action\":\"get_incidents\",\"object_id\":3}\n"
    "  «обнови здоровье сотрудника 7 на C»   → "
    "{\"action\":\"update_health\",\"employee_id\":7,\"new_class\":\"C\"}"
)

def ask_gemini(user_text: str) -> str:
    """
    • Сначала пытаемся использовать современный параметр system_instruction.
    • Если пакет старый и выдаёт TypeError, повторяем запрос без него,
      просто приклеив SYSTEM_PROMPT перед вопросом пользователя.
    • На выходе — ЧИСТЫЙ текст (без ```json обёрток).
    """
    if model is None:
        return "⚠️  Gemini отключён: нет API-ключа."

    gen_cfg = {"temperature": 0.3}

    # ── 1. «новый» способ ───────────────────────────
    try:
        if "system_instruction" in inspect.signature(model.generate_content).parameters:
            resp = model.generate_content(
                user_text,
                system_instruction=SYSTEM_PROMPT,
                generation_config=gen_cfg
            ).text
            return re.sub(r"^```[\s\S]*?\n|```$", "", resp).strip()
    except TypeError as e:
        # это именно “unexpected keyword” → пробуем старую схему
        if "unexpected keyword" not in str(e):
            return f"Ошибка Gemini: {e}"
    except Exception as e:
        return f"Ошибка Gemini: {e}"

    # ── 2. «старый» способ (склеиваем инструкции) ──
    try:
        prompt = f"{SYSTEM_PROMPT}\n\nПОЛЬЗОВАТЕЛЬ: {user_text}"
        resp = model.generate_content(prompt, generation_config=gen_cfg).text
        return re.sub(r"^```[\s\S]*?\n|```$", "", resp).strip()
    except Exception as e:
        tb = traceback.format_exc(limit=1)
        return f"Ошибка Gemini: {e}\n{tb}"


# ──────────────────── EEL API ────────────────────
@eel.expose
def get_all_data():
    data={}
    for tbl in ("Employees","Objects","Expenses"):
        rows=conn.execute(f"SELECT * FROM {tbl}").fetchall()
        data[tbl]=[dict(r) for r in rows]
    return data

ALLOWED = {
    "Employees":{"FullName","BirthDate","HealthClass","Role",
                 "Equipment","PatrolHistory","Warnings"},
    "Objects":{"ObjName","Lat","Lng","Criticality",
               "IncidentHistory","Rating"},
    "Expenses":{"Date","Item","Quantity","Cost","AssignedTo"}
}
@eel.expose
def update_record(table,rid,field,val):
    if table not in ALLOWED or field not in ALLOWED[table]:
        return "Недопустимое поле"
    if field in {"Warnings","Rating","Quantity","Cost","AssignedTo"}:
        val = int(val) if val not in ("",None) else None
    conn.execute(f"UPDATE {table} SET {field}=? WHERE ID=?",(val,rid))
    conn.commit()
    return "OK"

# ──────────────────── CHAT ENTRYPOINT ────────────────────
@eel.expose
def handle_query(user_text:str):
    reply = ask_gemini(user_text)

    # если Gemini вернул JSON-строку с action — выполняем
    try:
        cmd = json.loads(reply)
    except json.JSONDecodeError:
        return reply   # обычный текст

    if "action" not in cmd:
        return reply

    act = cmd["action"]

    if act == "get_incidents":
        oid = cmd.get("object_id")
        row = conn.execute("SELECT IncidentHistory FROM Objects WHERE ID=?", (oid,)).fetchone()
        return row["IncidentHistory"] if row else f"Объект {oid} не найден."

    if act == "get_patrols":
        eid = cmd.get("employee_id")
        row = conn.execute("SELECT PatrolHistory FROM Employees WHERE ID=?", (eid,)).fetchone()
        return row["PatrolHistory"] if row else f"Сотрудник {eid} не найден."

    if act == "update_health":
        eid  = cmd.get("employee_id")
        ncls = cmd.get("new_class","").upper()[:1]
        if ncls not in ("A","B","C"):
            return "Некорректный класс (A/B/C)."
        conn.execute("UPDATE Employees SET HealthClass=? WHERE ID=?", (ncls, eid))
        conn.commit()
        return f"Класс здоровья сотрудника {eid} обновлён на {ncls}."

    return "Команда не поддерживается."

# ──────────────────── RUN ────────────────────
if __name__ == "__main__":
    eel.init("web")
    eel.start("index.html", size=(1200, 800))
