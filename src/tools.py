import json
import threading
from .database import check_price, book_appointment, send_telegram_alert, log_event

# --- CUSTOM ORDERS ---
def calculate_custom_price(item_type, length, width, caller_id):
    try:
        l = int(length); w = int(width)
        area = (l * w) / 10000.0
        base = 50000
        cost = int(base + (area * 150000))
        
        msg = f"📏 **ХЭМЖЭЭНИЙ ХҮСЭЛТ**\n\n👤: {caller_id}\n🪑: {item_type} {l}x{w}\n💰: {cost}₮"
        threading.Thread(target=send_telegram_alert, args=(msg,)).start()
        return f"{item_type} {l} харьцах нь {w} хэмжээтэй хийхэд {cost} төгрөг болно."
    except: return "Тооцоолоход алдаа гарлаа."

def place_order(item_name, quantity, total_price, caller_id):
    msg = f"🛒 **БАТАЛГААЖСАН ЗАХИАЛГА!**\n\n👤: `{caller_id}`\n📦: {item_name}\n🔢: {quantity}\n💰: {total_price}"
    threading.Thread(target=send_telegram_alert, args=(msg,)).start()
    log_event(f"Order Placed: {item_name} x{quantity} by {caller_id}")
    return "Захиалгыг хүлээн авлаа."

# --- TOOL DEFINITIONS ---
TOOLS = [
    {"type": "function", "function": {"name": "check_price", "description": "Get product price.", "parameters": {"type": "object", "properties": {"product_name": {"type": "string"}}, "required": ["product_name"]}}},
    {"type": "function", "function": {"name": "calculate_custom_price", "description": "Calc custom furniture price.", "parameters": {"type": "object", "properties": {"item_type": {"type": "string"}, "length": {"type": "integer"}, "width": {"type": "integer"}}, "required": ["item_type", "length", "width"]}}},
    {"type": "function", "function": {"name": "place_order", "description": "Confirm order.", "parameters": {"type": "object", "properties": {"item_name": {"type": "string"}, "quantity": {"type": "integer"}, "total_price": {"type": "string"}}, "required": ["item_name", "quantity"]}}},
    {"type": "function", "function": {"name": "book_appointment", "description": "Book time.", "parameters": {"type": "object", "properties": {"time": {"type": "string"}}, "required": ["time"]}}},
    {"type": "function", "function": {"name": "transfer_call", "description": "Transfer call.", "parameters": {"type": "object", "properties": {}}}},
    {"type": "function", "function": {"name": "end_call", "description": "Hangup.", "parameters": {"type": "object", "properties": {}}}}
]

def handle_tool_call(tool_call, caller_id):
    fn = tool_call.function.name
    args = json.loads(tool_call.function.arguments)
    print(f"    🛠️  TOOL: {fn} -> {args}")
    
    res = "Done."
    should_transfer = False
    should_hangup = False
    
    if fn == "check_price": 
        res = check_price(args.get("product_name", ""))
    elif fn == "calculate_custom_price": 
        res = calculate_custom_price(args.get("item_type", ""), args.get("length", 0), args.get("width", 0), caller_id)
    elif fn == "place_order": 
        res = place_order(args.get("item_name", ""), args.get("quantity", 1), args.get("total_price", "Unknown"), caller_id)
    elif fn == "book_appointment": 
        res = book_appointment(args.get("time", ""), caller_id)
    elif fn == "transfer_call": 
        res = "Одоо холбож өгье."
        should_transfer = True
    elif fn == "end_call": 
        res = "Баяртай."
        should_hangup = True
        
    return res, should_transfer, should_hangup
