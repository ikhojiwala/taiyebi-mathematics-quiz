import os, random, sqlite3, time
from datetime import datetime
from html import escape
from flask import Flask, request, redirect, url_for, session, render_template_string, abort

SCHOOL_NAME = "TAIYEBI HIGHER SECONDARY SCHOOL UJJAIN"
DB_PATH = os.environ.get("DATABASE_PATH", "taiyebi_quiz.db")
DATABASE_URL = os.environ.get("DATABASE_URL", "").strip()
app = Flask(__name__)
app.secret_key = os.environ.get("SECRET_KEY", "change-this-before-deploying")
app.config.update(SESSION_COOKIE_HTTPONLY=True, SESSION_COOKIE_SAMESITE="Lax")

def db():
    if DATABASE_URL.startswith(("postgres://", "postgresql://")):
        import psycopg
        return psycopg.connect(DATABASE_URL, row_factory=psycopg.rows.dict_row), "pg"
    c = sqlite3.connect(DB_PATH, timeout=20)
    c.row_factory = sqlite3.Row
    return c, "sqlite"

def sql(c, kind, query, args=()):
    return c.execute(query.replace("?", "%s") if kind == "pg" else query, args)

def init_db():
    c,k=db()
    if k=="pg":
        sql(c,k,"""CREATE TABLE IF NOT EXISTS students(id BIGSERIAL PRIMARY KEY,full_name TEXT NOT NULL,roll TEXT NOT NULL,class_name INTEGER NOT NULL,created_at TEXT NOT NULL,UNIQUE(roll,class_name))""")
        sql(c,k,"""CREATE TABLE IF NOT EXISTS attempts(id BIGSERIAL PRIMARY KEY,student_id BIGINT NOT NULL REFERENCES students(id),level INTEGER NOT NULL,score INTEGER NOT NULL,total INTEGER NOT NULL,percentage DOUBLE PRECISION NOT NULL,passed INTEGER NOT NULL,completed_at TEXT NOT NULL,UNIQUE(student_id,level))""")
    else:
        sql(c,k,"""CREATE TABLE IF NOT EXISTS students(id INTEGER PRIMARY KEY AUTOINCREMENT,full_name TEXT NOT NULL,roll TEXT NOT NULL,class_name INTEGER NOT NULL,created_at TEXT NOT NULL,UNIQUE(roll,class_name))""")
        sql(c,k,"""CREATE TABLE IF NOT EXISTS attempts(id INTEGER PRIMARY KEY AUTOINCREMENT,student_id INTEGER NOT NULL,level INTEGER NOT NULL,score INTEGER NOT NULL,total INTEGER NOT NULL,percentage REAL NOT NULL,passed INTEGER NOT NULL,completed_at TEXT NOT NULL,UNIQUE(student_id,level),FOREIGN KEY(student_id) REFERENCES students(id))""")
    c.commit(); c.close()

# Create tables when the module is imported by a production server such as Gunicorn.
init_db()

LEVELS={1:{"name":"EASY","count":15,"minutes":5},2:{"name":"MEDIUM","count":20,"minutes":10},3:{"name":"HARD","count":25,"minutes":15}}
def bank(cls, level, count):
    r=random.Random(cls*1009+level*9176+2026); out=[]; seen=set()
    while len(out)<count:
        topic=r.randrange(5)
        if cls<=7:
            if topic==0: a,b=r.randint(10,99),r.randint(2,30); q=f"What is {a} + {b}?"; ans=a+b
            elif topic==1: a,b=r.randint(30,150),r.randint(2,29); a,b=max(a,b),min(a,b); q=f"What is {a} − {b}?"; ans=a-b
            elif topic==2: a,b=r.randint(2,15),r.randint(2,12); q=f"What is {a} × {b}?"; ans=a*b
            elif topic==3: b,a=r.randint(2,12),r.randint(2,15); q=f"What is {a*b} ÷ {b}?"; ans=a
            else: p=r.choice([10,20,25,50,75,100]); whole=r.choice([40,80,120,200]); q=f"What is {p}% of {whole}?"; ans=p*whole//100
        elif cls<=10:
            if topic==0: a,b=r.randint(2,15),r.randint(2,15); q=f"Simplify: {a}x + {b}x"; ans=f"{a+b}x"
            elif topic==1: x,a=r.randint(2,20),r.randint(1,12); q=f"Solve: x + {a} = {x+a}"; ans=x
            elif topic==2: a,b=r.randint(2,15),r.randint(2,15); q=f"Evaluate: {a}² + {b}"; ans=a*a+b
            elif topic==3: a,b=r.randint(3,20),r.randint(2,10); q=f"Rectangle perimeter: length {a}, width {b}"; ans=2*(a+b)
            else: a,b=r.randint(2,15),r.randint(2,15); q=f"Calculate: {a} × {b} − {a}"; ans=a*b-a
        else:
            if topic==0: a,b,d=r.randint(1,8),r.randint(1,8),r.randint(1,15); q=f"Differentiate: {a}x² + {b}x + {d}"; ans=f"{2*a}x + {b}"
            elif topic==1: a,b=r.randint(1,12),r.randint(1,12); q=f"Determinant of [[{a}, 1], [2, {b}]]"; ans=a*b-2
            elif topic==2: a,b=r.randint(2,12),r.randint(1,12); q=f"Evaluate {a}x when x = {b}"; ans=a*b
            elif topic==3: a,b=r.randint(2,10),r.randint(2,10); q=f"Expand: (x + {a})(x + {b})"; ans=f"x² + {a+b}x + {a*b}"
            else: a,b=r.randint(2,12),r.randint(2,12); q=f"Evaluate: {a}³ − {b}²"; ans=a**3-b**2
        key=(q,str(ans))
        if key in seen: continue
        seen.add(key)
        if isinstance(ans,int):
            wrong=set()
            while len(wrong)<3:
                v=ans+r.choice([-12,-9,-7,-5,-3,-2,-1,1,2,3,5,7,9,12])
                if v!=ans: wrong.add(v)
            options=[str(ans)]+[str(x) for x in wrong]
        else:
            options=[str(ans),str(ans).replace("+","−",1),str(ans).replace("x","y",1),str(ans)+" + 1"]
            options=list(dict.fromkeys(options))
            while len(options)<4: options.append(str(ans)+f" + {len(options)}")
        r.shuffle(options); out.append({"question":q,"answer":str(ans),"options":options[:4]})
    return out

CSS="""*{box-sizing:border-box}body{margin:0;background:#f3f6fb;color:#1b2b40;font-family:Arial,sans-serif}header{display:flex;align-items:center;gap:12px;padding:16px;background:linear-gradient(120deg,#0c2036,#204e78);color:#fff}.logo{width:54px;height:54px;display:grid;place-items:center;text-align:center;line-height:1.05;font-weight:900;color:#10243d;background:#fff1c9;border:3px solid #d8b44c;border-radius:50%;flex-shrink:0}header small{display:block;margin-top:5px;color:#d8e4ef}main{max-width:850px;margin:22px auto;padding:0 12px 50px}.card{background:#fff;border:1px solid #dfe7f0;border-radius:17px;padding:22px;margin:14px 0;box-shadow:0 12px 32px #10243d0b}h1{font-size:26px;margin:0 0 10px}h2{margin:12px 0}p{line-height:1.5}.muted{color:#718095}label{display:block;font-weight:700;margin:12px 0 5px}input,select{width:100%;padding:13px;border:1px solid #cbd6e2;border-radius:10px;font:inherit;background:#fff}button,.button{border:0;border-radius:10px;padding:13px 17px;background:#d8b44c;color:#201906;font-weight:800;font-size:14px;cursor:pointer;text-decoration:none;display:inline-block}.secondary{background:#204e78;color:#fff}.notice{background:#fff7df;color:#735400;border-radius:10px;padding:12px}.success{background:#e6f7ed;color:#175f3c;padding:14px;border-radius:12px}.error{background:#fff0f0;color:#a52a37;padding:14px;border-radius:12px}.options{display:grid;grid-template-columns:1fr 1fr;gap:10px;margin:16px 0}.option{background:#fbfcfe;color:#1b2b40;border:1px solid #dfe7f0;text-align:left}.option.selected{background:#edf6ff;border:2px solid #204e78}.row{display:flex;gap:10px;align-items:center;justify-content:space-between;flex-wrap:wrap}.bar{height:8px;background:#e9eef4;border-radius:10px;overflow:hidden;margin:15px 0}.bar span{display:block;height:100%;background:#d8b44c}@media(max-width:540px){.options{grid-template-columns:1fr}.card{padding:17px}h1{font-size:23px}}"""
def page(content,title="Taiyebi Mathematics Quiz"):
    return render_template_string("""<!doctype html><html><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>{{title}}</title><style>{{css}}</style></head><body><header><div class="logo">THS<br>UJJAIN</div><div><b>{{school}}</b><small>MATHEMATICS QUIZ • 2026</small></div></header><main>{{content|safe}}</main></body></html>""",title=title,css=CSS,school=SCHOOL_NAME,content=content)
def student(sid):
    c,k=db(); row=sql(c,k,"SELECT * FROM students WHERE id=?",(sid,)).fetchone(); c.close(); return row
def attempts(sid):
    c,k=db(); rows=sql(c,k,"SELECT * FROM attempts WHERE student_id=? ORDER BY level",(sid,)).fetchall(); c.close(); return {int(x["level"]):x for x in rows}
def sid(): return session.get("student_id")

@app.route("/")
def home():
    return page("""<section class="card"><div class="muted">WELCOME TO</div><h1>Taiyebi Mathematics Quiz</h1><p>Challenge yourself through three levels of mathematics.</p><div class="notice">One attempt per level • 60% pass mark • Progress saved</div><p><button class="button" type="button" onclick="enterQuiz()">🔊 ENTER QUIZ</button></p><p class="muted">Tap Enter Quiz to play the welcome sound and continue. Your browser requires a tap before it can play sound.</p></section><section class="card"><h2>Quiz levels</h2><p><b>Level 1 — Easy:</b> 15 questions · 5 minutes</p><p><b>Level 2 — Medium:</b> 20 questions · 10 minutes</p><p><b>Level 3 — Hard:</b> 25 questions · 15 minutes</p><p class="muted">Pass each level with 60% or more to unlock the next level.</p></section><script>
function enterQuiz(){
 try {
  const Ctx=window.AudioContext||window.webkitAudioContext;
  const ctx=new Ctx();
  const notes=[523.25,659.25,783.99];
  notes.forEach((freq,index)=>{
   const osc=ctx.createOscillator(); const gain=ctx.createGain();
   osc.type='sine'; osc.frequency.value=freq;
   const start=ctx.currentTime+index*0.13;
   gain.gain.setValueAtTime(0.0001,start);
   gain.gain.exponentialRampToValueAtTime(0.12,start+0.025);
   gain.gain.exponentialRampToValueAtTime(0.0001,start+0.20);
   osc.connect(gain); gain.connect(ctx.destination);
   osc.start(start); osc.stop(start+0.22);
  });
  setTimeout(()=>{window.location.href='/register';},550);
 } catch(e) { window.location.href='/register'; }
}
</script>""")
@app.route("/register",methods=["GET","POST"])
def register():
    if request.method=="GET":
        opts="".join(f'<option value="{x}">Class {x}</option>' for x in range(5,13))
        return page(f"""<section class="card"><h1>Student Registration</h1><p class="muted">Return with the same roll number and class to continue your progress.</p><form method="post"><label>Full name</label><input name="name" maxlength="100" required><label>Roll / enrollment number</label><input name="roll" maxlength="30" required><label>Class</label><select name="class_name" required><option value="">Choose class</option>{opts}</select><button>CONTINUE</button></form></section>""")
    name=request.form.get("name","").strip(); roll=request.form.get("roll","").strip()
    try: cls=int(request.form.get("class_name",""))
    except ValueError: cls=0
    if not name or not roll or cls not in range(5,13):
        return page('<section class="card error">Enter your name, roll number and a class from 5 to 12.</section><a class="button" href="/register">TRY AGAIN</a>')
    digits="".join(x for x in roll if x.isdigit())
    if digits and not digits.startswith(str(cls)):
        return page(f'<section class="card error">The roll number does not match Class {cls}. Check the number or contact your school.</section><a class="button" href="/register">TRY AGAIN</a>')
    c,k=db(); row=sql(c,k,"SELECT * FROM students WHERE roll=? AND class_name=?",(roll,cls)).fetchone()
    if row:
        stid=row["id"]; sql(c,k,"UPDATE students SET full_name=? WHERE id=?",(name,stid))
    else:
        cur=sql(c,k,"INSERT INTO students(full_name,roll,class_name,created_at) VALUES(?,?,?,?) RETURNING id",(name,roll,cls,datetime.utcnow().isoformat()))
        got=cur.fetchone(); stid=got["id"] if k=="pg" else got[0]
    c.commit(); c.close(); session["student_id"]=stid
    return redirect(url_for("dashboard"))
@app.route("/dashboard")
def dashboard():
    if not sid(): return redirect(url_for("register"))
    st=student(sid())
    if not st: session.clear(); return redirect(url_for("register"))
    done=attempts(sid()); nextlvl=0
    for lv in (1,2,3):
        if lv not in done:
            if all(k in done and done[k]["passed"] for k in range(1,lv)): nextlvl=lv
            break
    rows=""
    for lv,info in LEVELS.items():
        if lv in done:
            a=done[lv]; rows+=f'<p><b>Level {lv} — {info["name"]}:</b> {a["score"]}/{a["total"]} ({a["percentage"]:.0f}%) · {"PASSED" if a["passed"] else "NOT PASSED"}</p>'
        else:
            locked=any(k not in done or not done[k]["passed"] for k in range(1,lv))
            rows+=f'<p><b>Level {lv} — {info["name"]}:</b> {"LOCKED" if locked else "READY"}</p>'
    action=f'<p><a class="button" href="/begin/{nextlvl}">START LEVEL {nextlvl} — {LEVELS[nextlvl]["name"]}</a></p>' if nextlvl else '<div class="success"><b>All three levels completed.</b><p>Thank you for participating!</p></div>'
    return page(f'<section class="card"><div class="muted">STUDENT DASHBOARD</div><h1>Welcome, {escape(st["full_name"])}</h1><p>Class {st["class_name"]} · Roll {escape(st["roll"])}</p><h2>Your progress</h2>{rows}{action}<a class="button secondary" href="/logout">EXIT</a></section>')
@app.route("/begin/<int:level>")
def begin(level):
    if not sid(): return redirect(url_for("register"))
    if level not in LEVELS: abort(404)
    done=attempts(sid())
    if level in done or any(k not in done or not done[k]["passed"] for k in range(1,level)): return redirect(url_for("dashboard"))
    q=bank(student(sid())["class_name"],level,LEVELS[level]["count"])
    session["active"]={"level":level,"questions":q,"end":time.time()+LEVELS[level]["minutes"]*60}
    session["answers"]={}
    return redirect(url_for("quiz"))
@app.route("/quiz")
def quiz():
    active=session.get("active")
    if not sid() or not active: return redirect(url_for("dashboard" if sid() else "register"))
    qs=active["questions"]; idx=max(0,min(int(request.args.get("q","0")),len(qs)-1)); q=qs[idx]
    chosen=session.get("answers",{}).get(str(idx),""); rem=max(0,int(active["end"]-time.time()))
    opts="".join(f'<button type="button" class="option {"selected" if chosen==o else ""}" onclick="pick({idx},{i})">{chr(65+i)}. {escape(o)}</button>' for i,o in enumerate(q["options"]))
    pct=int((idx+1)/len(qs)*100)
    nxt=f'<a class="button secondary" href="/quiz?q={idx+1}">NEXT</a>' if idx<len(qs)-1 else ""
    return page(f"""<section class="card"><div class="row"><b>LEVEL {active['level']} — {LEVELS[active['level']]['name']}</b><span class="notice" id="timer">Time left</span></div><div class="bar"><span style="width:{pct}%"></span></div><p class="muted">QUESTION {idx+1} OF {len(qs)}</p><h2>{escape(q['question'])}</h2><div class="options">{opts}</div><div class="row"><a class="button secondary" href="/quiz?q={max(0,idx-1)}">PREVIOUS</a>{nxt}<button onclick="finish()">SUBMIT LEVEL</button></div><p class="muted">Once submitted, this level cannot be retaken.</p></section><script>
let end={active['end']*1000};function tick(){{let n=Math.max(0,Math.floor((end-Date.now())/1000));document.getElementById('timer').textContent='Time left: '+String(Math.floor(n/60)).padStart(2,'0')+':'+String(n%60).padStart(2,'0');if(n<=0)location.href='/submit?auto=1';else setTimeout(tick,500)}}tick();
function pick(q,i){{fetch('/answer',{{method:'POST',headers:{{'Content-Type':'application/json'}},body:JSON.stringify({{q:q,i:i}})}}).then(()=>location.reload())}}
function finish(){{if(confirm('Submit this level now? You cannot retake it.'))location.href='/submit'}}
</script>""")
@app.route("/answer",methods=["POST"])
def answer():
    a=session.get("active")
    if not sid() or not a:return ("",401)
    d=request.get_json(silent=True) or {}
    try:q=int(d["q"]);i=int(d["i"])
    except Exception:return ("",400)
    if not 0<=q<len(a["questions"]) or not 0<=i<4:return ("",400)
    ans=session.get("answers",{});ans[str(q)]=a["questions"][q]["options"][i];session["answers"]=ans
    return ("",204)
@app.route("/submit")
def submit():
    a=session.get("active")
    if not sid() or not a:return redirect(url_for("dashboard" if sid() else "register"))
    lv=a["level"]; done=attempts(sid())
    if lv in done:session.pop("active",None);session.pop("answers",None);return redirect(url_for("dashboard"))
    qs=a["questions"]; answers=session.get("answers",{})
    score=sum(answers.get(str(i))==q["answer"] for i,q in enumerate(qs)); total=len(qs); pct=round(score*100/total,2); passed=int(pct>=60)
    c,k=db();sql(c,k,"INSERT INTO attempts(student_id,level,score,total,percentage,passed,completed_at) VALUES(?,?,?,?,?,?,?)",(sid(),lv,score,total,pct,passed,datetime.utcnow().isoformat()));c.commit();c.close()
    session.pop("active",None);session.pop("answers",None)
    return redirect(url_for("dashboard"))
@app.route("/logout")
def logout():session.clear();return redirect(url_for("home"))
if __name__=="__main__":
    app.run(host="0.0.0.0",port=int(os.environ.get("PORT","8080")),debug=False)
