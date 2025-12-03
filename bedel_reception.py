IP = get_local_ip()

rtp_sequence = 0
rtp_timestamp = 0
current_sip_addr = None
current_caller_id = "Unknown"
current_call_id = None
conversation_history = [] 

# --- LOGGING FUNCTION ---
def log_event(text):
    """Үйл явдлыг файлд бичих"""
    timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    try:
        with open(LOG_FILE, "a", encoding="utf-8") as f:
            f.write(f"[{timestamp}] {text}\n")
    except: pass

# --- TELEGRAM FUNCTION ---
def send_telegram_alert(message):
    """Telegram руу мессеж илгээх"""
    if "YOUR_BOT" in TELEGRAM_BOT_TOKEN: return
    
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    payload = {
        "chat_id": TELEGRAM_CHAT_ID,
        "text": f"🤖 *BEDEL AI:*\n{message}",
        "parse_mode": "Markdown"
    }
    try:
        requests.post(url, json=payload, timeout=3)
        print("[*] 📲 Telegram SENT successfully!")
        log_event(f"Telegram Sent: {message}")
    except Exception as e:
        print(f"[!] Telegram Failed: {e}")

# --- NUMBER CONVERTER ---
def num2mongolian(n):
    try: n = int(re.sub(r'[^\d]', '', str(n)))
    except: return ""
    units = ["", "нэг", "хоёр", "гурав", "дөрөв", "тав", "зургаа", "долоо", "найм", "ес"]
    tens = ["", "арав", "хорин", "гучин", "дөчин", "тавин", "жаран", "далан", "наян", "ерэн"]
    power = ["", "мянган", "сая", "тэрбум"]
    if n == 0: return "тэг"
    def cvt(num):
        s = ""
        if num >= 100: s += units[num // 100] + " зуун "; num %= 100
        if num >= 10: s += tens[num // 10] + " "; num %= 10
        if num > 0: s += units[num] + " "
        return s.strip()
    parts = []; count = 0
    while n > 0:
        chunk = n % 1000
        if chunk > 0:
            p = cvt(chunk)
            if count > 0: p += " " + power[count]
            parts.insert(0, p)
        n //= 1000; count += 1
    return " ".join(parts).strip()

def convert_numbers(text):
    def repl(m): return num2mongolian(m.group())
    return re.sub(r'\d+', repl, text)

# --- DATABASE MANAGER ---
def init_db():
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS products (name TEXT, price INTEGER, description TEXT)''')
    c.execute('''CREATE TABLE IF NOT EXISTS bookings (time TEXT, info TEXT)''')
    
    # BEDEL TECH PRODUCTS (Furniture + IT)
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

def db_check_price(query):
    print(f"[DB] Searching for: {query}")
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

def db_book(time_str):
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute("INSERT INTO bookings (time, info) VALUES (?, ?)", (time_str, current_caller_id))
    conn.commit(); conn.close()
    
    msg = f"📅 *ШИНЭ ЗАХИАЛГА!*\n\n📞 Дугаар: `{current_caller_id}`\n⏰ Цаг: {time_str}"
    threading.Thread(target=send_telegram_alert, args=(msg,)).start()
    return f"За, {time_str}-д бүртгэлээ."

# --- CUSTOM ORDERS ---
def calculate_custom_price(item_type, length, width):
    try:
        l = int(length); w = int(width)
        area = (l * w) / 10000.0
        base = 50000
        cost = int(base + (area * 150000))
        
        msg = f"📏 **ХЭМЖЭЭНИЙ ХҮСЭЛТ**\n\n👤: {current_caller_id}\n🪑: {item_type} {l}x{w}\n💰: {cost}₮"
        threading.Thread(target=send_telegram_alert, args=(msg,)).start()
        return f"{item_type} {l} харьцах нь {w} хэмжээтэй хийхэд {cost} төгрөг болно."
    except: return "Тооцоолоход алдаа гарлаа."

def place_order(item_name, quantity, total_price):
    msg = f"🛒 **БАТАЛГААЖСАН ЗАХИАЛГА!**\n\n👤: `{current_caller_id}`\n📦: {item_name}\n🔢: {quantity}\n💰: {total_price}"
    threading.Thread(target=send_telegram_alert, args=(msg,)).start()
    log_event(f"Order Placed: {item_name} x{quantity} by {current_caller_id}")
    return "Захиалгыг хүлээн авлаа."

# --- CLEANER (BUG FIXED) ---
def clean_text_for_tts(text):
    text = text.replace("\n", ". ").replace(",", "")
    replacements = {"BEDEL Tech": "Бэ дэл Тэк", "Nomad Tech": "Бэ дэл Тэк"}
    for eng, mon in replacements.items(): text = text.replace(eng, mon)
    text = re.sub(r'[a-zA-Z]', '', text)
    text = convert_numbers(text)
    text = re.sub(r'[^\w\s\u0400-\u04FF.?!]', ' ', text)
    
    # FIX: Indentation logic zasav
    if len(text) > 280: 
        text = text[:280]
        last_dot = text.rfind(".")
        if last_dot > 50: 
            text = text[:last_dot+1]
    
    return text.strip()

# --- STATE ---
class State: IDLE=0; LISTENING=1; PROCESSING=2; SPEAKING=3
current_state = State.IDLE
audio_buffer = []
silence_start_time = None

# --- TOOLS ---
tools = [
    {"type": "function", "function": {"name": "check_price", "description": "Get product price.", "parameters": {"type": "object", "properties": {"product_name": {"type": "string"}}, "required": ["product_name"]}}},
    {"type": "function", "function": {"name": "calculate_custom_price", "description": "Calc custom furniture price.", "parameters": {"type": "object", "properties": {"item_type": {"type": "string"}, "length": {"type": "integer"}, "width": {"type": "integer"}}, "required": ["item_type", "length", "width"]}}},
    {"type": "function", "function": {"name": "place_order", "description": "Confirm order.", "parameters": {"type": "object", "properties": {"item_name": {"type": "string"}, "quantity": {"type": "integer"}, "total_price": {"type": "string"}}, "required": ["item_name", "quantity"]}}},
    {"type": "function", "function": {"name": "book_appointment", "description": "Book time.", "parameters": {"type": "object", "properties": {"time": {"type": "string"}}, "required": ["time"]}}},
    {"type": "function", "function": {"name": "transfer_call", "description": "Transfer call.", "parameters": {"type": "object", "properties": {}}}},
    {"type": "function", "function": {"name": "end_call", "description": "Hangup.", "parameters": {"type": "object", "properties": {}}}}
]

# --- SIP ACTIONS ---
def send_sip_refer(sock, target_ip, target_port):
    if not current_caller_id or not current_call_id: return
    print(f"[*] 🔄 TRANSFER...")
    threading.Thread(target=send_telegram_alert, args=(f"⚠️ OPERATOR NEEDED: {current_caller_id}",)).start()
    msg = f"REFER sip:{current_caller_id}@{target_ip} SIP/2.0\r\nVia: SIP/2.0/UDP {IP}:{SIP_PORT};branch=z9hG4bK{int(time.time())}\r\nFrom: <sip:ai@{IP}>;tag=srv\r\nTo: <sip:{current_caller_id}@{target_ip}>\r\nCall-ID: {current_call_id}\r\nCSeq: 102 REFER\r\nContact: <sip:ai@{IP}:{SIP_PORT}>\r\nRefer-To: <sip:{OPERATOR_EXT}@{target_ip}>\r\nContent-Length: 0\r\n\r\n"
    sock.sendto(msg.encode(), (target_ip, target_port))

def send_sip_bye(sock, target_ip, target_port):
    if not current_caller_id or not current_call_id: return
    print(f"[*] 📞 HANGUP...")
    msg = f"BYE sip:{current_caller_id}@{target_ip} SIP/2.0\r\nVia: SIP/2.0/UDP {IP}:{SIP_PORT};branch=z9hG4bK{int(time.time())}\r\nFrom: <sip:ai@{IP}>;tag=srv\r\nTo: <sip:{current_caller_id}@{target_ip}>\r\nCall-ID: {current_call_id}\r\nCSeq: 103 BYE\r\nContent-Length: 0\r\n\r\n"
    sock.sendto(msg.encode(), (target_ip, target_port))

# --- PIPELINE ---
def process_audio(client_ip, client_port, sock, sip_sock, sip_addr):
    global current_state, conversation_history
    print("\n[1] 🎙️  Processing...")
    current_state = State.PROCESSING
    
    try:
        raw = b''.join(audio_buffer)
        if len(raw) < 1600: print("[!] Short audio"); start_listening(); return
        pcm = audioop.ulaw2lin(raw, 2)
        with wave.open(INPUT_FILE, 'wb') as f:
            f.setnchannels(1); f.setsampwidth(2); f.setframerate(8000); f.setcomptype('NONE', 'NONE')
            f.writeframes(pcm)
    except: start_listening(); return

    print("[2] ☁️  STT...")
    user_text = ""
    try:
        h = {"Token": CHIMEGE_SST_TOKEN, "Content-Type": "application/octet-stream", "Punctuate": "true"}
        with open(INPUT_FILE, "rb") as f:
            r = requests.post("https://api.chimege.com/v1.2/transcribe", headers=h, data=f)
            r.encoding = 'utf-8'
            if r.status_code == 200: 
                user_text = r.text.strip()
                print(f"    🗣️  User: {user_text}")
                log_event(f"User: {user_text}")
            else: start_listening(); return
    except: start_listening(); return

    print("[3] 🧠  Thinking...")
    ai_resp = ""
    should_transfer = False; should_hangup = False

    try:
        client = OpenAI()
        # CURRENT TIME
        now_str = datetime.datetime.now().strftime("%Y-%m-%d %H:%M")
        
        sys_prompt = f"""
        Чи бол 'BEDEL Tech' (Бэ дэл Тэк) компанийн борлуулалтын зөвлөх.
        Өнөөдөр: {now_str}.
        
        [КОМПАНИЙН МЭДЭЭЛЭЛ]
        - Хаяг: Улаанбаатар хот, Сүхбаатар дүүрэг, Нэгдүгээр хороо, Тэдий төвийн ард.
        - Ажлын цаг: Есөн цагаас хорин цаг хүртэл.
        - Үйл ажиллагаа: Оффис тавилга (Ширээ, Сандал, Шүүгээ) болон IT шийдэл (Yeastar, IP утас).

        [ДҮРЭМ]
        1. Зөвхөн Кирилл Монголоор хариул. ТООГ ҮСГЭЭР БИЧ.
        2. Үнэ асуувал `check_price`.
        3. `check_price` "Not_Found" гэвэл: "Уучлаарай, одоогоор алга" гэж хэл.
        4. "Захиалъя" гэвэл `place_order`.
        5. Хэмжээгээр захиална гэвэл `calculate_custom_price`.
        6. Оператортай ярья гэвэл `transfer_call`.
        """
        
        if not conversation_history: conversation_history.append({"role": "system", "content": sys_prompt})
        conversation_history.append({"role": "user", "content": user_text})
        
        # Simple Memory Management
        if len(conversation_history) > 10:
             conversation_history = [conversation_history[0]] + conversation_history[-5:]

        comp = client.chat.completions.create(model="gpt-4o-mini", messages=conversation_history, tools=tools, tool_choice="auto")
        msg = comp.choices[0].message
        
        if msg.tool_calls:
            conversation_history.append(msg)
            for tool in msg.tool_calls:
                fn = tool.function.name
                args = json.loads(tool.function.arguments)
                print(f"    🛠️  TOOL: {fn} -> {args}")
                res = "Done."
                if fn == "check_price": res = db_check_price(args.get("product_name", ""))
                elif fn == "calculate_custom_price": res = calculate_custom_price(args.get("item_type", ""), args.get("length", 0), args.get("width", 0))
                elif fn == "place_order": res = place_order(args.get("item_name", ""), args.get("quantity", 1), args.get("total_price", "Unknown"))
                elif fn == "book_appointment": res = db_book(args.get("time", ""))
                elif fn == "transfer_call": res = "Одоо холбож өгье."; should_transfer = True
                elif fn == "end_call": res = "Баяртай."; should_hangup = True
                
                conversation_history.append({"role": "tool", "tool_call_id": tool.id, "content": str(res)})
            
            comp2 = client.chat.completions.create(model="gpt-4o-mini", messages=conversation_history)
            ai_resp = comp2.choices[0].message.content
        else: ai_resp = msg.content
        
        conversation_history.append({"role": "assistant", "content": ai_resp})
        ai_resp = clean_text_for_tts(ai_resp)
        print(f"    🤖  AI: {ai_resp}")
        log_event(f"AI: {ai_resp}")

    except Exception as e: 
        print(f"[!] Brain Error: {e}"); ai_resp = "Уучлаарай алдаа гарлаа."
        conversation_history = []

    print("[4] 👄  TTS...")
    try:
        h = {"Token": CHIMEGE_TTS_TOKEN, "Content-Type": "text/plain"}
        r = requests.post("https://api.chimege.com/v1.2/synthesize", headers=h, data=ai_resp.encode('utf-8'))
        if r.status_code == 200:
            with open(OUTPUT_FILE, "wb") as f: f.write(r.content)
            play_audio(client_ip, client_port, sock)
            if should_transfer and sip_addr: time.sleep(2); send_sip_refer(sip_sock, sip_addr[0], sip_addr[1])
            elif should_hangup and sip_addr: time.sleep(2); send_sip_bye(sip_sock, sip_addr[0], sip_addr[1])
        else: print(f"[!] TTS Error: {r.text}"); start_listening()
    except: start_listening()

def start_listening():
    global current_state, audio_buffer, silence_start_time
    print("\n[*] 👂 Listening...")
    audio_buffer = []
    silence_start_time = None
    current_state = State.LISTENING

def play_audio(target_ip, target_port, sock):
    global current_state, rtp_sequence, rtp_timestamp
    current_state = State.SPEAKING
    print(f"[*] 🔊 Playing to {target_ip}:{target_port}")
    if not os.path.exists(OUTPUT_FILE): start_listening(); return
    try:
        with wave.open(OUTPUT_FILE, 'rb') as wf:
            content = wf.readframes(wf.getnframes())
            rate = wf.getframerate(); width = wf.getsampwidth(); channels = wf.getnchannels()
            if rate != 8000: content, _ = audioop.ratecv(content, width, channels, rate, 8000, None)
            if channels == 2: content = audioop.tomono(content, width, 0.5, 0.5)
            offset = 0
            while offset < len(content) and current_state == State.SPEAKING:
                chunk = content[offset:offset+320]
                offset += 320
                if len(chunk) < 320: chunk += b'\x00'*(320-len(chunk))
                sock.sendto(struct.pack('!BBHII', 0x80, 0, rtp_sequence, rtp_timestamp, 12345) + audioop.lin2ulaw(chunk, 2), (target_ip, target_port))
                rtp_sequence += 1; rtp_timestamp += 160; time.sleep(0.02)
    except: pass
    start_listening()

def rtp_engine(sock, sip_sock):
    global current_state, audio_buffer, silence_start_time, current_sip_addr
    print(f"[*] RTP Listening...")
    while True:
        try:
            data, addr = sock.recvfrom(4096)
            if current_state == State.LISTENING and len(data) > 12:
                payload = data[12:]
                rms = audioop.rms(payload, 1)
                if rms > SILENCE_THRESHOLD: audio_buffer.append(payload); silence_start_time = None
                else:
                    if len(audio_buffer) > 0:
                        if silence_start_time is None: silence_start_time = time.time()
                        elif (time.time() - silence_start_time) > SILENCE_LIMIT:
                            if len(audio_buffer) > MIN_AUDIO_LEN:
                                threading.Thread(target=process_audio, args=(addr[0], addr[1], sock, sip_sock, current_sip_addr)).start()
                                current_state = State.PROCESSING
                            else: audio_buffer = []; silence_start_time = None
        except: pass

def send_hole_punch(sock, target_ip, target_port):
    global rtp_sequence, rtp_timestamp
    silence = b'\xff' * 160
    for i in range(50):
        hdr = struct.pack('!BBHII', 0x80, 0, rtp_sequence, rtp_timestamp, 12345)
        sock.sendto(hdr + silence, (target_ip, target_port))
        rtp_sequence += 1; rtp_timestamp += 160; time.sleep(0.02)

def create_resp(code, txt, req, to_tag=None, sdp=False):
    def g(n): 
        for l in req.split("\r\n"): 
            if l.lower().startswith(n.lower()+":"): return l.split(":",1)[1].strip()
        return ""
    s = ""
    if sdp: s = f"v=0\r\no=- 1 1 IN IP4 {IP}\r\ns=Py\r\nc=IN IP4 {IP}\r\nt=0 0\r\nm=audio {RTP_PORT} RTP/AVP 0\r\na=rtpmap:0 PCMU/8000\r\na=sendrecv\r\n"
    return (f"SIP/2.0 {code} {txt}\r\nVia: {g('Via')}\r\nFrom: {g('From')}\r\nTo: {g('To') + (f';tag={to_tag}' if to_tag and 'tag=' not in g('To') else '')}\r\nCall-ID: {g('Call-ID')}\r\nCSeq: {g('CSeq')}\r\nContact: <sip:{IP}:{SIP_PORT}>\r\nContent-Type: application/sdp\r\nContent-Length: {len(s)}\r\n\r\n{s}").encode()

def run_server():
    init_db()
    try:
        sip = socket.socket(socket.AF_INET, socket.SOCK_DGRAM); sip.bind(("0.0.0.0", SIP_PORT))
        rtp = socket.socket(socket.AF_INET, socket.SOCK_DGRAM); rtp.bind(("0.0.0.0", RTP_PORT))
    except OSError: print("[!] PORT ERROR: Хуучин python-оо хаа!"); return

    threading.Thread(target=rtp_engine, args=(rtp, sip), daemon=True).start()
    print(f"[*] 🇲🇳 BEDEL TECH PLATINUM (LOGGING) READY! {IP}")
    
    global rtp_sequence, rtp_timestamp, current_sip_addr, current_caller_id, current_call_id, conversation_history
    def parse_port(r, default):
        try:
             body = r.split("\r\n\r\n")[1]
             for l in body.split("\r\n"):
                 if l.startswith("m=audio"): return int(l.split(" ")[1])
        except: pass
        return default
    def get_header(req, name):
        for l in req.split("\r\n"):
            if l.lower().startswith(name.lower()+":"): return l.split(":",1)[1].strip()
        return ""

    while True:
        try:
            d, a = sip.recvfrom(4096); r = d.decode(errors='ignore')
            if "INVITE" in r:
                print(f"\n[+] Call: {a}"); start_listening()
                current_sip_addr = a 
                from_hdr = get_header(r, "From")
                if "sip:" in from_hdr: current_caller_id = from_hdr.split("sip:")[1].split("@")[0]
                current_call_id = get_header(r, "Call-ID")
                conversation_history = [] 
                sip.sendto(create_resp(100, "Trying", r), a)
                sip.sendto(create_resp(180, "Ringing", r, "t"), a)
                sip.sendto(create_resp(200, "OK", r, "t", True), a)
                rtp_sequence = 0; rtp_timestamp = 0
                client_rtp_port = parse_port(r, a[1]+2)
                threading.Thread(target=send_hole_punch, args=(rtp, a[0], client_rtp_port)).start()
            elif "BYE" in r: print("\n[-] End"); sip.sendto(create_resp(200, "OK", r), a); start_listening()
            elif "REGISTER" in r: sip.sendto(create_resp(200, "OK", r, "r"), a)
        except: pass

if __name__ == "__main__":
    run_server()