"""
Amazon Price + Israel Shipping Tracker
רץ כל שעה דרך cron, שולח אימייל אם המחיר ירד + יש שילוח חינם לישראל
"""

import requests
from bs4 import BeautifulSoup
import smtplib
import json
import os
from email.mime.text import MIMEText
from datetime import datetime

# ─── הגדרות ───────────────────────────────────────────

PRODUCTS = [
    {
        "name": "Sony WH-1000XM5",
        "url": "https://www.amazon.com/dp/B09XS7JWHH",
        "threshold": 280,   # שלח התראה אם המחיר מתחת ל-$280
    },
    # הוסף מוצרים נוספים כאן:
    # {
    #     "name": "שם המוצר",
    #     "url": "https://www.amazon.com/dp/XXXXXXXXXX",
    #     "threshold": 100,
    # },
]

# אימייל — מלא כאן או הגדר כ-env variables
EMAIL_SENDER   = os.getenv("EMAIL_SENDER",   "your@gmail.com")
EMAIL_PASSWORD = os.getenv("EMAIL_PASSWORD", "xxxx xxxx xxxx xxxx")
EMAIL_RECEIVER = os.getenv("EMAIL_RECEIVER", "your@gmail.com")

HISTORY_FILE = "tracker_history.json"

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/124.0.0.0 Safari/537.36"
    ),
    "Accept-Language": "en-US,en;q=0.9",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
}

# ─── שליפת מידע ───────────────────────────────────────

def get_product_info(product: dict) -> dict | None:
    try:
        r = requests.Session().get(product["url"], headers=HEADERS, timeout=15)
        r.raise_for_status()
    except Exception as e:
        log(f"שגיאת רשת: {e}")
        return None

    soup = BeautifulSoup(r.text, "html.parser")

    price    = extract_price(soup)
    shipping = check_israel_free_shipping(soup)

    return {
        "name":     product["name"],
        "url":      product["url"],
        "price":    price,
        "shipping": shipping,
        "time":     datetime.now().isoformat(),
    }


def extract_price(soup) -> float | None:
    for sel in [
        ("span", "a-price-whole"),
        ("span", "priceblock_ourprice"),
        ("span", "priceblock_dealprice"),
        ("span", "a-offscreen"),
    ]:
        el = soup.find(sel[0], class_=sel[1]) or soup.find(sel[0], id=sel[1])
        if el:
            raw = el.get_text(strip=True).replace(",", "").replace("$", "").replace("\xa0", "")
            try:
                return float(raw.split(".")[0])
            except ValueError:
                continue
    return None


def check_israel_free_shipping(soup) -> dict:
    """
    בודק שני דברים:
    1. האם יש שילוח לישראל
    2. האם הוא חינמי בקנייה מעל $49
    """
    # נחפש את בלוק המשלוח
    block = (
        soup.find("div", id="deliveryBlockMessage") or
        soup.find("div", id="mir-layout-DELIVERY_BLOCK") or
        soup.find("div", id="delivery-message")
    )
    text = block.get_text(" ", strip=True).lower() if block else ""

    # בדיקת ישראל
    ships_to_israel = "israel" in text or "il " in text

    # בדיקת חינם מ-$49
    free_over_49 = (
        ships_to_israel and
        ("free" in text or "חינם" in text) and
        "49" in text
    )

    return {
        "ships_to_israel": ships_to_israel,
        "free_over_49":    free_over_49,
    }

# ─── היסטוריה ─────────────────────────────────────────

def load_history() -> dict:
    if os.path.exists(HISTORY_FILE):
        with open(HISTORY_FILE) as f:
            return json.load(f)
    return {}


def save_history(history: dict):
    with open(HISTORY_FILE, "w") as f:
        json.dump(history, f, indent=2, ensure_ascii=False)

# ─── התראה ────────────────────────────────────────────

def send_alert(info: dict, threshold: float):
    ship = info["shipping"]
    shipping_line = (
        "✅ שילוח חינם לישראל בקנייה מעל $49!"
        if ship["free_over_49"]
        else "📦 יש שילוח לישראל (בתשלום)"
        if ship["ships_to_israel"]
        else "❌ אין שילוח לישראל"
    )

    body = f"""🚨 התראת מחיר — {info['name']}

💰 מחיר נוכחי: ${info['price']:.0f}
🎯 רף שהגדרת: ${threshold:.0f}
✈️  שילוח:     {shipping_line}

🔗 {info['url']}
⏰ {info['time']}
"""
    msg = MIMEText(body, "plain", "utf-8")
    msg["Subject"] = f"🚨 Amazon: {info['name']} — ${info['price']:.0f}"
    msg["From"]    = EMAIL_SENDER
    msg["To"]      = EMAIL_RECEIVER

    try:
        with smtplib.SMTP_SSL("smtp.gmail.com", 465) as s:
            s.login(EMAIL_SENDER, EMAIL_PASSWORD)
            s.send_message(msg)
        log(f"📧 אימייל נשלח: {info['name']} ${info['price']}")
    except Exception as e:
        log(f"שגיאת אימייל: {e}")

# ─── לוג ──────────────────────────────────────────────

def log(msg: str):
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M")
    line = f"[{timestamp}] {msg}"
    print(line)
    with open("tracker.log", "a") as f:
        f.write(line + "\n")

# ─── ריצה ─────────────────────────────────────────────

def main():
    log(f"▶ מתחיל בדיקה — {len(PRODUCTS)} מוצרים")
    history = load_history()

    for product in PRODUCTS:
        info = get_product_info(product)
        if not info:
            log(f"⚠ נכשל: {product['name']}")
            continue

        price = info["price"]
        ship  = info["shipping"]
        log(f"  {product['name']}: ${price} | ישראל={ship['ships_to_israel']} | חינם={ship['free_over_49']}")

        # ── תנאי שליחת התראה ──
        price_ok    = price is not None and price < product["threshold"]
        shipping_ok = ship["free_over_49"]

        if price_ok and shipping_ok:
            # שלח התראה רק אם לא שלחנו כבר על אותו מחיר
            last = history.get(product["url"], {}).get("last_alert_price")
            if last is None or price < last:
                send_alert(info, product["threshold"])
                info["last_alert_price"] = price

        # שמור בהיסטוריה
        history[product["url"]] = {
            "last_price":       price,
            "last_alert_price": info.get("last_alert_price",
                                history.get(product["url"], {}).get("last_alert_price")),
            "last_check":       info["time"],
        }

    save_history(history)
    log("✅ סיום בדיקה")


if __name__ == "__main__":
    main()
