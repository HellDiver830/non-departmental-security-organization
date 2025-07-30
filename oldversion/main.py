
"""
Sci‑Fi Security HUD — v0.8 (fixed)
----------------------------------

Запуск:
    pip install eel pyodbc google-generativeai pandas pywin32
    set GEMINI_API_KEY=<ваш‑ключ>
    python main.py
"""
import os, json, random, threading, queue, time, pathlib
from datetime import date, timedelta
import eel, pyodbc

# ───────── CONFIG ─────────
DB_FILE = "security.accdb"
ADMIN_USER = "admin"
ADMIN_PASS = "admin123"
GEMINI_KEY = os.getenv("GEMINI_API_KEY", "")
WEB_DIR = "web"

# ───────── DB SCHEMA ─────────
SCHEMA = {
    "Candidates":
        ("CREATE TABLE Candidates ("
         "ID AUTOINCREMENT PRIMARY KEY, "
         "FullName TEXT, "
         "BirthDate DATE, "
         "HealthClass TEXT)"),

    "Objects":
        ("CREATE TABLE Objects ("
         "ID AUTOINCREMENT PRIMARY KEY, "
         "ObjName TEXT, "
         "Lat DOUBLE, "
         "Lng DOUBLE, "
         "Criticality INTEGER)")
}

def _create_blank_db(path: str):
    import win32com.client as win32
    cat = win32.Dispatch("ADOX.Catalog")
    cat.Create(f"Provider=Microsoft.ACE.OLEDB.12.0;Data Source={os.path.abspath(path)};")

def _conn():
    conn_str = (r"Driver={Microsoft Access Driver (*.mdb, *.accdb)};"
                f"DBQ={os.path.abspath(DB_FILE)};")
    return pyodbc.connect(conn_str, autocommit=True)


def ensure_db():
    if not os.path.exists(DB_FILE):
        print("[INIT] Creating blank .accdb …")
        _create_blank_db(DB_FILE)

    con = _conn()
    cur = con.cursor()

    existing = {t.table_name for t in cur.tables(tableType="TABLE")}
    for tbl, ddl in SCHEMA.items():
        if tbl not in existing:
            print(f"[INIT] Creating table {tbl}")
            cur.execute(ddl)

    # ---------- seed demo data ----------
    # add objects if table empty
    cur.execute("SELECT COUNT(*) FROM Objects")
    if cur.fetchone()[0] == 0:
        obj_rows = []
        for i in range(10):
            lat = random.uniform(-40, 40)
            lng = random.uniform(-90, 90)
            obj_rows.append((
                f"Site-{i+1}",
                lat,
                lng,
                random.randint(1, 5)
            ))
        cur.executemany(
            "INSERT INTO Objects (ObjName,Lat,Lng,Criticality) VALUES (?,?,?,?)",
            obj_rows
        )
        print("[SEED] Inserted demo Objects")

    # add candidates if empty
    cur.execute("SELECT COUNT(*) FROM Candidates")
    if cur.fetchone()[0] == 0:
        cand_rows = []
        surnames = ["Ivanov", "Smirnov", "Kuznetsov", "Popov", "Sokolov",
                    "Lebedev", "Kozlov", "Novikov", "Morozov", "Petrov"]
        for i in range(10):
            full = f"{random.choice(surnames)} {random.choice(['Aleksey','Oleg','Igor','Viktor','Sergey'])}"
            bdate = date.today() - timedelta(days=random.randint(20*365, 45*365))
            cand_rows.append((
                full,
                bdate.strftime("%Y-%m-%d"),
                random.choice(["A", "B", "C"])
            ))
        cur.executemany(
            "INSERT INTO Candidates (FullName,BirthDate,HealthClass) VALUES (?,?,?)",
            cand_rows
        )
        print("[SEED] Inserted demo Candidates")

    con.commit()
    cur.close()
    con.close()


# ───────── Eel exposed helpers ─────────
def fetch_rows(table):
    con=_conn(); cur=con.cursor()
    cur.execute(f"SELECT * FROM {table}")
    cols=[d[0] for d in cur.description]
    res=[dict(zip(cols,r)) for r in cur.fetchall()]
    cur.close(); con.close(); return res

@eel.expose
def api_tables():
    return list(SCHEMA)

@eel.expose
def api_rows(tbl):
    return fetch_rows(tbl)

@eel.expose
def api_update(tbl,row_id,col,val):
    con=_conn(); cur=con.cursor()
    cur.execute(f"UPDATE {tbl} SET [{col}]=? WHERE ID=?", (val, row_id))
    con.commit(); cur.close(); con.close()
    return True

# globe data
@eel.expose
def api_globe():
    objs = fetch_rows("Objects")
    guards=[]
    for o in objs:
        guards.append({
            "id":100+o["ID"],
            "type":"guard",
            "lat":o["Lat"]+random.uniform(-1,1),
            "lng":o["Lng"]+random.uniform(-1,1)
        })
    return {"objects":objs,"guards":guards}

# Gemini chat
@eel.expose
def ai_chat(prompt:str):
    if not GEMINI_KEY:
        return "(AI disabled)"
    try:
        import google.generativeai as genai
        genai.configure(api_key=GEMINI_KEY)
        model = genai.GenerativeModel("gemini-pro")
        resp = model.generate_content(prompt, generation_config={"temperature":0.3})
        return resp.text
    except Exception as e:
        return f"error: {e}"

# ───────── HTML generation ─────────
CSS_GLOBE = """
.scene{width:100%;height:100%;display:flex;justify-content:center;align-items:center;perspective:1200px}
.wrapper{width:50vmin;height:50vmin;transform-style:preserve-3d;transform:rotateX(-8deg)}
.globe{width:100%;height:100%;position:relative;transform-style:preserve-3d;animation:spin 25s linear infinite}
.ring{position:absolute;width:100%;height:100%;border:2px dotted var(--c);border-radius:50%;opacity:0;animation:fade .8s ease forwards}
@keyframes spin{to{transform:rotateY(-360deg)}}
@keyframes fade{to{opacity:1}}
"""

HTML_TEMPLATE = """
<!doctype html>
<html><head><meta charset='utf-8'><title>HUD</title>
<link href='https://fonts.googleapis.com/css2?family=Orbitron:wght@400;600&display=swap' rel='stylesheet'>
<style>
:root{--c:#00e0ff;--c2:#0088ff}
*{box-sizing:border-box}body{{margin:0;background:#000018;color:var(--c);font-family:'Orbitron',sans-serif}}
section{{padding:4px;border-top:1px solid var(--c2)}}
button,input,select{{background:#002033;color:var(--c);border:1px solid var(--c2);padding:4px 6px;font-family:inherit}}
button:hover{{background:#003850}}
#orb{{height:40vh}}
#chatZone{{height:25vh;display:flex;flex-direction:column}}
#log{{flex:1;overflow-y:auto;border:1px solid var(--c2);padding:4px;font-size:13px}}
#grid{{height:35vh;overflow:auto;border:1px solid var(--c2)}}
.table th,.table td{{padding:2px 6px;border:1px solid var(--c2)}}
{css_globe}
</style>
</head>
<body>
<section id=login>
  <h3>SECURE LOGIN</h3>
  <input id=u placeholder=user>
  <input id=p placeholder=pass type=password>
  <button onclick="L()">Enter</button><span id=err></span>
</section>

<section id=orb hidden>
  <div class="scene"><div class="wrapper"><div class="globe">
    {rings}
  </div></div></div>
</section>

<section id=chatZone hidden>
  <div id=log></div>
  <div><input id=q style="width:80%">
       <button onclick=send()>Send</button>
  </div>
</section>

<section id=dataSec hidden>
  <select id=tables onchange=load()></select>
  <button onclick=load()>Refresh</button>
  <div id=grid></div>
</section>

<script>
const ADMIN='{admin}',PASS='{pwd}';
function L(){if(u.value===ADMIN&&p.value===PASS){login.remove();orb.hidden=chatZone.hidden=dataSec.hidden=false;init();}else err.textContent='❌';}

async function init(){
  tables.innerHTML=(await eel.api_tables()()).map(t=>`<option>${t}</option>`).join('');
  load(); drawPoints();
}

async function load(){
  const t=tables.value;
  const rows=await eel.api_rows(t)();
  if(!rows.length){grid.textContent='(empty)';return;}
  const keys=Object.keys(rows[0]);
  let h='<table class="table"><tr>'+keys.map(k=>`<th>${k}</th>`).join('')+'</tr>';
  rows.forEach(r=>{
    h+='<tr>'+keys.map(c=>`<td contenteditable onblur="eel.api_update('${t}',${r.ID},'${c}',this.textContent)">${r[c]??''}</td>`).join('')+'</tr>';
  });
  grid.innerHTML=h;
}

async function send(){
  const txt=q.value.trim();
  if(!txt) return;
  addLine('> '+txt);
  q.value='';
  const wait=addLine('<i>assistant…</i>',true);
  const ans=await eel.ai_chat(txt)();
  wait.remove(); addLine(ans);
}

function addLine(html,ret=false){
  const d=document.createElement('div'); d.innerHTML=html; log.appendChild(d); log.scrollTop=log.scrollHeight; return d;
}

async function drawPoints(){
  const data=await eel.api_globe()();
  const container=document.querySelector('.globe');
  data.objects.forEach(o=>{
    const pt=document.createElement('span');
    pt.className='ring'; // reuse CSS
    const lat=o.Lat* Math.PI/180, lng=o.Lng*Math.PI/180;
    const r=50; // %
    const x=r*Math.cos(lat)*Math.sin(lng);
    const y=r*Math.sin(lat);
    const z=r*Math.cos(lat)*Math.cos(lng);
    pt.style.transform=`translate3d(${x}%,${y}%,${z}px) scale(.05)`;
    container.appendChild(pt);
  });
}

</script>
</body></html>
"""

def build_html():
    # генерируем 7 колец с задержкой анимации
    rings = "\n".join(
        "<span class='ring' style='animation-delay:{}ms'></span>".format(i * 120)
        for i in range(7)
    )

    # подставляем данные простым .replace() – никаких фигурных скобок не ломаем
    html = (HTML_TEMPLATE
            .replace("{css_globe}", CSS_GLOBE)
            .replace("{rings}", rings)
            .replace("{admin}", ADMIN_USER)
            .replace("{pwd}", ADMIN_PASS))

    pathlib.Path(WEB_DIR).mkdir(exist_ok=True)
    pathlib.Path(WEB_DIR, "index.html").write_text(html, encoding="utf-8")



# ───────── MAIN ─────────
if __name__ == "__main__":
    ensure_db()
    build_html()
    eel.init(WEB_DIR)
    eel.start("index.html", size=(1280,720))
