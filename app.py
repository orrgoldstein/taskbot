"""
TaskBot - Telegram Bot + Web Dashboard
בוט טלגרם לניהול משימות עם דשבורד ווב
מסד נתונים: Neon PostgreSQL (חינמי לצמיתות)
"""

import os
import re
import logging
import asyncio
from datetime import datetime
from flask import Flask, render_template, jsonify, request
from telegram import Update, Bot
from telegram.ext import Application, CommandHandler, ContextTypes
import psycopg2
from psycopg2.extras import RealDictCursor

# ============================================================
# הגדרות
# ============================================================

TELEGRAM_TOKEN = os.environ.get("TELEGRAM_TOKEN", "")
RENDER_EXTERNAL_URL = os.environ.get("RENDER_EXTERNAL_URL", "")
DATABASE_URL = os.environ.get("DATABASE_URL", "")
PORT = int(os.environ.get("PORT", 10000))
SECRET_PATH = os.environ.get("SECRET_PATH", "webhook-secret-path")

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# ============================================================
# מסד נתונים - Neon PostgreSQL
# ============================================================

def get_db():
    conn = psycopg2.connect(DATABASE_URL, sslmode="require")
    conn.autocommit = True
    return conn

def init_db():
    conn = get_db()
    cur = conn.cursor()
    cur.execute("""
        CREATE TABLE IF NOT EXISTS tasks (
            id SERIAL PRIMARY KEY,
            text TEXT NOT NULL,
            assignee TEXT NOT NULL DEFAULT 'לא משויך',
            priority TEXT NOT NULL DEFAULT 'בינונית',
            status TEXT NOT NULL DEFAULT 'לביצוע',
            created_at TEXT NOT NULL,
            created_by TEXT DEFAULT '',
            telegram_user_id BIGINT
        )
    """)
    cur.execute("""
        CREATE TABLE IF NOT EXISTS team_members (
            id SERIAL PRIMARY KEY,
            name TEXT UNIQUE NOT NULL
        )
    """)
    cur.execute("SELECT COUNT(*) FROM team_members")
    if cur.fetchone()[0] == 0:
        cur.execute("INSERT INTO team_members (name) VALUES ('מנהל')")
    cur.close()
    conn.close()
    logger.info("✅ Database initialized")

def get_all_tasks():
    conn = get_db()
    cur = conn.cursor(cursor_factory=RealDictCursor)
    cur.execute("SELECT * FROM tasks ORDER BY id DESC")
    tasks = [dict(t) for t in cur.fetchall()]
    cur.close()
    conn.close()
    return tasks

def get_team_members():
    conn = get_db()
    cur = conn.cursor()
    cur.execute("SELECT name FROM team_members ORDER BY id")
    members = [row[0] for row in cur.fetchall()]
    cur.close()
    conn.close()
    return members

def db_add_task(text, assignee, priority, created_by="", telegram_user_id=None):
    conn = get_db()
    cur = conn.cursor(cursor_factory=RealDictCursor)
    created_at = datetime.now().strftime("%d/%m %H:%M")
    cur.execute(
        """INSERT INTO tasks (text, assignee, priority, status, created_at, created_by, telegram_user_id)
           VALUES (%s, %s, %s, 'לביצוע', %s, %s, %s) RETURNING *""",
        (text, assignee, priority, created_at, created_by, telegram_user_id)
    )
    task = dict(cur.fetchone())
    cur.close()
    conn.close()
    return task

def update_task_status(task_id, new_status):
    conn = get_db()
    cur = conn.cursor(cursor_factory=RealDictCursor)
    cur.execute("UPDATE tasks SET status = %s WHERE id = %s RETURNING *", (new_status, task_id))
    task = cur.fetchone()
    cur.close()
    conn.close()
    return dict(task) if task else None

def add_team_member(name):
    conn = get_db()
    cur = conn.cursor()
    try:
        cur.execute("INSERT INTO team_members (name) VALUES (%s)", (name,))
    except psycopg2.errors.UniqueViolation:
        pass
    cur.close()
    conn.close()

def remove_team_member(name):
    conn = get_db()
    cur = conn.cursor()
    cur.execute("DELETE FROM team_members WHERE name = %s", (name,))
    cur.execute("UPDATE tasks SET assignee = 'לא משויך' WHERE assignee = %s", (name,))
    cur.close()
    conn.close()

# ============================================================
# פקודות הבוט
# ============================================================

async def cmd_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "🤖 שלום! אני הבוט לניהול משימות\n\n"
        "📖 פקודות זמינות:\n\n"
        "/הוסף [משימה] @[שם] ![עדיפות]\n"
        "/בוצע [מספר]\n"
        "/סטטוס [מספר] [סטטוס]\n"
        "/רשימה - כל המשימות\n"
        "/שלי - המשימות שלי\n"
        "/צוות - רשימת חברי הצוות\n"
        "/עזרה - הצגת פקודות\n\n"
        "💡 גם הפקודות באנגלית עובדות!"
    )

async def cmd_help(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await cmd_start(update, context)

async def cmd_add(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = " ".join(context.args) if context.args else ""
    if not text:
        await update.message.reply_text("❌ חסר טקסט למשימה\nדוגמה: /הוסף להכין מצגת @דני !גבוהה")
        return

    members = get_team_members()
    assignee = update.effective_user.first_name or "לא משויך"
    
    assignee_match = re.search(r"@(\S+)", text)
    if assignee_match:
        name = assignee_match.group(1)
        found = [m for m in members if name in m]
        if found:
            assignee = found[0]
        else:
            await update.message.reply_text(
                f'❌ לא נמצא איש צוות בשם "{name}"\n\n'
                f"👥 חברי צוות זמינים:\n{', '.join(members)}\n\n"
                "נסה שוב עם שם מהרשימה, או שלח בלי @ כדי לשייך אליך."
            )
            return

    priority = "בינונית"
    if "!גבוהה" in text:
        priority = "גבוהה"
    elif "!נמוכה" in text:
        priority = "נמוכה"

    task_text = re.sub(r"@\S+", "", text)
    task_text = re.sub(r"!גבוהה|!נמוכה|!בינונית", "", task_text).strip()
    if not task_text:
        await update.message.reply_text("❌ חסר טקסט למשימה")
        return

    task = db_add_task(task_text, assignee, priority,
                       update.effective_user.first_name or "לא ידוע",
                       update.effective_user.id)

    priority_emoji = {"גבוהה": "🔴", "בינונית": "🟡", "נמוכה": "🟢"}.get(priority, "⚪")
    await update.message.reply_text(
        f'✅ משימה #{task["id"]} נוספה:\n"{task_text}"\n\n👤 {assignee}\n{priority_emoji} עדיפות: {priority}'
    )

async def cmd_done(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.args:
        await update.message.reply_text("❌ חסר מספר משימה\nדוגמה: /בוצע 3")
        return
    try:
        task_id = int(context.args[0])
    except ValueError:
        await update.message.reply_text("❌ מספר משימה לא תקין")
        return

    task = update_task_status(task_id, "הושלם")
    if not task:
        await update.message.reply_text(f"❌ לא נמצאה משימה #{task_id}")
        return
    await update.message.reply_text(f'✅ משימה #{task_id} סומנה כהושלמה:\n"{task["text"]}"')

async def cmd_status(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if len(context.args) < 2:
        await update.message.reply_text("❌ חסרים פרטים\nדוגמה: /סטטוס 3 בתהליך\n\nסטטוסים: לביצוע / בתהליך / הושלם")
        return
    try:
        task_id = int(context.args[0])
    except ValueError:
        await update.message.reply_text("❌ מספר משימה לא תקין")
        return

    new_status = " ".join(context.args[1:])
    if new_status not in ["לביצוע", "בתהליך", "הושלם"]:
        await update.message.reply_text(f"❌ סטטוס לא מוכר. השתמש ב: לביצוע / בתהליך / הושלם")
        return

    task = update_task_status(task_id, new_status)
    if not task:
        await update.message.reply_text(f"❌ לא נמצאה משימה #{task_id}")
        return
    await update.message.reply_text(f"🔄 משימה #{task_id} עודכנה ל: {new_status}")

async def cmd_list(update: Update, context: ContextTypes.DEFAULT_TYPE):
    open_tasks = [t for t in get_all_tasks() if t["status"] != "הושלם"]
    if not open_tasks:
        await update.message.reply_text("🎉 אין משימות פתוחות!")
        return
    lines = []
    for t in open_tasks:
        pe = {"גבוהה": "🔴", "בינונית": "🟡", "נמוכה": "🟢"}.get(t["priority"], "⚪")
        se = {"לביצוע": "⬜", "בתהליך": "🔄"}.get(t["status"], "⬜")
        lines.append(f'{se} #{t["id"]} {t["text"]}\n   👤 {t["assignee"]} {pe}')
    await update.message.reply_text(f"📋 משימות פתוחות ({len(open_tasks)}):\n\n" + "\n\n".join(lines))

async def cmd_my(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_name = update.effective_user.first_name or ""
    my_tasks = [
        t for t in get_all_tasks()
        if t["status"] != "הושלם" and (
            t.get("telegram_user_id") == update.effective_user.id or user_name in t["assignee"]
        )
    ]
    if not my_tasks:
        await update.message.reply_text("🎉 אין לך משימות פתוחות!")
        return
    lines = []
    for t in my_tasks:
        pe = {"גבוהה": "🔴", "בינונית": "🟡", "נמוכה": "🟢"}.get(t["priority"], "⚪")
        lines.append(f'#{t["id"]} {t["text"]} {pe}')
    await update.message.reply_text(f"📋 המשימות שלך ({len(my_tasks)}):\n\n" + "\n".join(lines))

async def cmd_team(update: Update, context: ContextTypes.DEFAULT_TYPE):
    members = get_team_members()
    tasks = get_all_tasks()
    lines = []
    for m in members:
        c = len([t for t in tasks if t["assignee"] == m and t["status"] != "הושלם"])
        lines.append(f"👤 {m} — {c} משימות פתוחות")
    await update.message.reply_text(f"👥 חברי צוות ({len(members)}):\n\n" + "\n".join(lines))

# ============================================================
# Flask
# ============================================================

app = Flask(__name__)

@app.route("/")
def dashboard():
    return render_template("dashboard.html")

@app.route("/api/tasks")
def api_tasks():
    return jsonify({"tasks": get_all_tasks(), "team_members": get_team_members()})

@app.route("/api/tasks", methods=["POST"])
def api_add_task():
    b = request.json
    task = db_add_task(b.get("text",""), b.get("assignee","לא משויך"), b.get("priority","בינונית"), "דשבורד")
    return jsonify(task)

@app.route("/api/tasks/<int:task_id>/status", methods=["PUT"])
def api_update_status(task_id):
    task = update_task_status(task_id, request.json.get("status",""))
    if not task:
        return jsonify({"error": "not found"}), 404
    return jsonify(task)

@app.route("/api/team", methods=["POST"])
def api_add_member():
    name = request.json.get("name","").strip()
    if name:
        add_team_member(name)
    return jsonify({"team_members": get_team_members()})

@app.route("/api/team/<name>", methods=["DELETE"])
def api_remove_member(name):
    remove_team_member(name)
    return jsonify({"team_members": get_team_members()})

@app.route(f"/{SECRET_PATH}", methods=["POST"])
def telegram_webhook():
    asyncio.run(process_update(request.get_json(force=True)))
    return "ok"

telegram_app = None

async def process_update(update_data):
    global telegram_app
    if telegram_app:
        update = Update.de_json(update_data, telegram_app.bot)
        await telegram_app.process_update(update)

async def setup_telegram():
    global telegram_app
    if not TELEGRAM_TOKEN:
        logger.warning("⚠️ TELEGRAM_TOKEN not set - bot disabled")
        return
    
    telegram_app = Application.builder().token(TELEGRAM_TOKEN).build()
    for cmd_he, cmd_en, handler in [
        ("הוסף","add",cmd_add), ("בוצע","done",cmd_done), ("סטטוס","status",cmd_status),
        ("רשימה","list",cmd_list), ("שלי","my",cmd_my), ("צוות","team",cmd_team), ("עזרה","help",cmd_help),
    ]:
        telegram_app.add_handler(CommandHandler(cmd_he, handler))
        telegram_app.add_handler(CommandHandler(cmd_en, handler))
    telegram_app.add_handler(CommandHandler("start", cmd_start))
    await telegram_app.initialize()

    if RENDER_EXTERNAL_URL:
        webhook_url = f"{RENDER_EXTERNAL_URL}/{SECRET_PATH}"
        await Bot(TELEGRAM_TOKEN).set_webhook(webhook_url)
        logger.info(f"✅ Webhook set: {webhook_url}")

# ============================================================
# הפעלה
# ============================================================

if __name__ == "__main__":
    if DATABASE_URL:
        init_db()
        logger.info("✅ Connected to Neon PostgreSQL")
    else:
        logger.error("❌ DATABASE_URL not set! Get it from https://console.neon.tech")
    
    asyncio.run(setup_telegram())
    logger.info(f"🚀 Server starting on port {PORT}")
    app.run(host="0.0.0.0", port=PORT)
