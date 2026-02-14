# 🤖 TaskBot — מדריך התקנה

## מה זה?
בוט טלגרם לניהול משימות צוותי + דשבורד ווב.  
הכל חינמי לצמיתות: Render (שרת) + Neon (מסד נתונים) + Telegram (בוט).

---

## שלב 1: יצירת בוט בטלגרם

1. פתח Telegram וחפש **@BotFather**
2. שלח `/newbot`
3. תן שם ו-username לבוט
4. **שמור את ה-API Token** — תצטרך אותו בשלב 4

---

## שלב 2: יצירת מסד נתונים ב-Neon (חינמי לצמיתות)

1. לך ל-[console.neon.tech](https://console.neon.tech) וצור חשבון חינמי
2. לחץ **Create Project** ותן שם (למשל `taskbot`)
3. בחר Region קרוב אליך (למשל `AWS eu-central-1` לאירופה)
4. אחרי היצירה, **העתק את ה-Connection String** — זה נראה ככה:
   ```
   postgresql://username:password@ep-xxxxx.eu-central-1.aws.neon.tech/neondb?sslmode=require
   ```
5. **שמור את ה-Connection String** — תצטרך אותו בשלב 4

> 💡 Neon חינמי לצמיתות: 0.5GB אחסון, 100 CU-hours/חודש — יותר ממספיק לבוט משימות

---

## שלב 3: העלאת הקוד ל-GitHub

1. צור Repository חדש ב-GitHub
2. בתיקייה של הפרויקט:

```bash
git init
git add .
git commit -m "TaskBot initial commit"
git branch -M main
git remote add origin https://github.com/YOUR_USERNAME/taskbot.git
git push -u origin main
```

---

## שלב 4: הגדרה ב-Render

1. לך ל-[render.com](https://render.com) > **New > Web Service**
2. חבר את ה-GitHub Repository
3. הגדר:
   - **Name:** `taskbot`
   - **Runtime:** `Python`
   - **Build Command:** `pip install -r requirements.txt`
   - **Start Command:** `python app.py`
   - **Plan:** `Free`

4. הוסף **Environment Variables**:

| Key | Value | מאיפה? |
|-----|-------|--------|
| `TELEGRAM_TOKEN` | ה-Token מ-BotFather | שלב 1 |
| `DATABASE_URL` | ה-Connection String מ-Neon | שלב 2 |
| `SECRET_PATH` | מחרוזת אקראית (למשל `wh-abc123`) | תבחר בעצמך |
| `RENDER_EXTERNAL_URL` | `https://taskbot.onrender.com` | ה-URL מ-Render |

5. לחץ **Create Web Service**

---

## שלב 5: אימות

1. **דשבורד:** גלוש ל-URL של Render
2. **בוט:** חפש את הבוט בטלגרם ושלח `/start`
3. נסה: `/הוסף לבדוק שהכל עובד !גבוהה`
4. רענן את הדשבורד — המשימה מופיעה!

---

## מבנה הקבצים

```
taskbot/
├── app.py                  # בוט + שרת + חיבור ל-DB
├── requirements.txt        # תלויות Python
├── render.yaml             # הגדרות Render
├── templates/
│   └── dashboard.html      # דשבורד ווב
└── README.md               # המדריך הזה
```

---

## ארכיטקטורה

```
┌─────────────┐     ┌──────────────────┐     ┌─────────────┐
│  Telegram   │────▶│  Render (Python) │────▶│    Neon      │
│  משתמשים    │◀────│  Flask + Bot     │◀────│  PostgreSQL  │
└─────────────┘     └──────────────────┘     └─────────────┘
                           │    ▲
                           ▼    │
                    ┌──────────────────┐
                    │   דשבורד ווב     │
                    │   (דפדפן)        │
                    └──────────────────┘
```

---

## פקודות הבוט

| פקודה | תיאור | דוגמה |
|-------|--------|-------|
| `/הוסף` | הוספת משימה | `/הוסף להכין מצגת @דני !גבוהה` |
| `/בוצע` | סימון כהושלם | `/בוצע 3` |
| `/סטטוס` | עדכון סטטוס | `/סטטוס 3 בתהליך` |
| `/רשימה` | משימות פתוחות | `/רשימה` |
| `/שלי` | המשימות שלי | `/שלי` |
| `/צוות` | חברי הצוות | `/צוות` |
| `/עזרה` | הצגת פקודות | `/עזרה` |

> גם באנגלית: `/add`, `/done`, `/status`, `/list`, `/my`, `/team`, `/help`

---

## עלויות

| רכיב | שירות | עלות |
|------|-------|------|
| שרת | Render Free | $0 |
| מסד נתונים | Neon Free | $0 |
| בוט | Telegram API | $0 |
| **סה"כ** | | **$0 לצמיתות** |

---

## הערות

- **Render Free** — השרת נרדם אחרי 15 דקות. ההודעה הראשונה אחרי שינה לוקחת ~30 שניות.
- **Neon Free** — הנתונים נשמרים לצמיתות (לא פוגים!). מוגבל ל-0.5GB — מספיק לאלפי משימות.
- שני השירותים לא דורשים כרטיס אשראי.
