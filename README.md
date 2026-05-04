# 📦 Amazon Price Tracker

בודק כל שעה אם מוצר באמזון ירד מתחת למחיר מסוים **ויש שילוח חינם לישראל בקנייה מעל $49**.

## הגדרה

### 1. הוסף מוצרים ב-`tracker.py`
```python
PRODUCTS = [
    {
        "name": "שם המוצר",
        "url": "https://www.amazon.com/dp/XXXXXXXXXX",
        "threshold": 200,   # שלח התראה מתחת ל-$200
    },
]
```

### 2. הגדר Secrets ב-GitHub
Settings → Secrets and variables → Actions → New repository secret

| Secret | ערך |
|--------|-----|
| `EMAIL_SENDER` | כתובת Gmail שולחת |
| `EMAIL_PASSWORD` | App Password מ-Google |
| `EMAIL_RECEIVER` | כתובת האימייל שלך |

> **App Password:** myaccount.google.com → Security → 2-Step Verification → App passwords

### 3. זהו!
GitHub מריץ אוטומטית כל שעה. אפשר גם להפעיל ידנית מ-Actions → Run workflow.

## לוגים
כל ריצה נשמרת ב-Actions tab ב-GitHub.
