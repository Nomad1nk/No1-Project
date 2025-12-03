import sqlite3
import threading
from .config import DB_FILE, LOG_FILE, TELEGRAM_BOT_TOKEN, TELEGRAM_CHAT_ID
import datetime
import requests

def log_event(text):
    timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    try:
        with open(LOG_FILE, "a", encoding="utf-8") as f:
            f.write(f"[{timestamp}] {text}\n")
    except: pass

def send_telegram_alert(message):
    if not TELEGRAM_BOT_TOKEN or "YOUR_BOT" in TELEGRAM_BOT_TOKEN: return
    
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    payload = {
        "chat_id": TELEGRAM_CHAT_ID,
        "text": f"🤖 *BEDEL AI:*\n{message}",
        "parse_mode": "Markdown"
    }
    try:
        requests.post(url, json=payload, timeout=3)
        log_event(f"Telegram Sent: {message}")
    except Exception as e:
        print(f"[!] Telegram Failed: {e}")

def init_db():
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS products (name TEXT, price INTEGER, description TEXT)''')
    c.execute('''CREATE TABLE IF NOT EXISTS bookings (time TEXT, info TEXT)''')
    
    products = [
        ("Оффис ширээ", 150000, "120х60см стандарт"), ("Арьсан сандал", 250000, "Эргономик"),
        ("Компьютерын ширээ", 120000, "100х50см"), ("Шүүгээ", 65000, "3 тавцантай"),
        ("Тавиур", 12000, "Бүх төрлийн тавиур"), ("Шкаф", 18000, "Бүх төрлийн шкаф"),
        ("Yeastar TG100", 450000, "VoIP Gateway"), ("IP Утас", 120000, "HD Voice"),
        ("Суурилуулалт", 50000, "Инженер"), ("Үйлчилгээ", 5000, "Техник үйлчилгээ"),
    ]
    for p in products:
        c.execute("SELECT count(*) FROM products WHERE name=?", (p[0],))
        if c.fetchone()[0] == 0:
            c.execute("INSERT INTO products (name, price, description) VALUES (?, ?, ?)", p)
    conn.commit()
    conn.close()

def check_price(query):
    query = query.lower().replace(" ", "")
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute("SELECT name, price, description FROM products")
    all_products = c.fetchall()
    conn.close()
    
    found_items = []
    for name, price, desc in all_products:
        if query in name.lower().replace(" ", ""):
            found_items.append(f"{name}: {price}₮ ({desc})")
            
    if found_items: return " | ".join(found_items[:3])
    else: return "Not_Found"

def book_appointment(time_str, caller_id):
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute("INSERT INTO bookings (time, info) VALUES (?, ?)", (time_str, caller_id))
    conn.commit(); conn.close()
    
    msg = f"📅 *ШИНЭ ЗАХИАЛГА!*\n\n📞 Дугаар: `{caller_id}`\n⏰ Цаг: {time_str}"
    threading.Thread(target=send_telegram_alert, args=(msg,)).start()
    return f"За, {time_str}-д бүртгэлээ."
