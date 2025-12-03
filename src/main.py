import socket
import threading
import time
import os
import requests
import json
import wave
import warnings
warnings.filterwarnings("ignore", category=DeprecationWarning)
import audioop
from openai import OpenAI
from .config import (
    SIP_PORT, RTP_PORT, BIND_IP, CHIMEGE_SST_TOKEN, CHIMEGE_TTS_TOKEN, 
    OPENAI_API_KEY, INPUT_FILE_PREFIX, OUTPUT_FILE_PREFIX, OPERATOR_EXT,
    RTP_TARGET_IP
)
from .database import init_db, log_event
from .session import CallSession, CallState
from .sip import create_response, parse_port, get_header, create_refer, create_bye
from .rtp import send_hole_punch, play_audio
from .tools import TOOLS, handle_tool_call
from .license import verify_license, get_mac_address

# Global Sessions: { (ip, port): CallSession }
sessions = {}
sessions_lock = threading.Lock()

def check_license():
    # Read license from file or env
    license_key = os.getenv("LICENSE_KEY", "")
    if not verify_license(license_key):
        print("\n" + "="*50)
        print("❌ LICENSE ERROR: Invalid License Key!")
        print(f"🔒 Device MAC: {get_mac_address()}")
        print("Please contact Bedel Tech to purchase a license.")
        print("="*50 + "\n")
        # In production, you might want to exit() here
        # exit(1) 
        return False
    print("✅ License Verified.")
    return True


def get_session(addr):
    with sessions_lock:
        return sessions.get(addr)

def create_session(addr, call_id, caller_id):
    with sessions_lock:
        session = CallSession(call_id, caller_id, addr)
        sessions[addr] = session
        return session

def remove_session(addr):
    with sessions_lock:
        if addr in sessions:
            del sessions[addr]

# --- AI PROCESSING ---
def process_ai(session, audio_data, sock):
    print(f"[{session.call_id}] 🎙️  Processing Audio...")
    
    # 1. Save Audio
    input_filename = f"{INPUT_FILE_PREFIX}{session.call_id}.wav"
    try:
        pcm = audioop.ulaw2lin(audio_data, 2)
        with wave.open(input_filename, 'wb') as f:
            f.setnchannels(1); f.setsampwidth(2); f.setframerate(8000); f.setcomptype('NONE', 'NONE')
            f.writeframes(pcm)
    except Exception as e:
        print(f"[!] Audio Save Error: {e}")
        session.state = CallState.LISTENING
        return

    # 2. STT (Chimege)
    print(f"[{session.call_id}] ☁️  STT...")
    user_text = ""
    try:
        h = {"Token": CHIMEGE_SST_TOKEN, "Content-Type": "application/octet-stream", "Punctuate": "true"}
        with open(input_filename, "rb") as f:
            r = requests.post("https://api.chimege.com/v1.2/transcribe", headers=h, data=f)
            r.encoding = 'utf-8'
            if r.status_code == 200: 
                user_text = r.text.strip()
                print(f"    🗣️  User ({session.caller_id}): {user_text}")
                log_event(f"User ({session.caller_id}): {user_text}")
            else: 
                print(f"[!] STT Failed: {r.status_code}")
                session.state = CallState.LISTENING
                return
    except Exception as e:
        print(f"[!] STT Error: {e}")
        session.state = CallState.LISTENING
        return

    if not user_text:
        print(f"[*] Empty speech (Noise?), ignoring.")
        session.state = CallState.LISTENING
        return

    # 3. LLM (OpenAI)
    print(f"[{session.call_id}] 🧠  Thinking...")
    ai_resp = ""
    should_transfer = False
    should_hangup = False

    try:
        client = OpenAI(api_key=OPENAI_API_KEY)
        session.conversation_history.append({"role": "user", "content": user_text})
        
        # Memory Management
        if len(session.conversation_history) > 10:
             session.conversation_history = [session.conversation_history[0]] + session.conversation_history[-5:]

        comp = client.chat.completions.create(
            model="gpt-4o-mini", 
            messages=session.conversation_history, 
            tools=TOOLS, 
            tool_choice="auto"
        )
        msg = comp.choices[0].message
        
        if msg.tool_calls:
            session.conversation_history.append(msg)
            for tool in msg.tool_calls:
                res, transfer, hangup = handle_tool_call(tool, session.caller_id)
                if transfer: should_transfer = True
                if hangup: should_hangup = True
                
                session.conversation_history.append({
                    "role": "tool", 
                    "tool_call_id": tool.id, 
                    "content": str(res)
                })
            
            comp2 = client.chat.completions.create(
                model="gpt-4o-mini", 
                messages=session.conversation_history
            )
            ai_resp = comp2.choices[0].message.content
        else:
            ai_resp = msg.content
        
        session.conversation_history.append({"role": "assistant", "content": ai_resp})
        
        # Clean text (Simple version)
        ai_resp = ai_resp.replace("\n", ". ").strip()
        from .utils import clean_text_for_tts
        ai_resp = clean_text_for_tts(ai_resp)
        if len(ai_resp) > 290:
            ai_resp = ai_resp[:290] + "..."
        
        print(f"    🤖  AI: {ai_resp}")
        log_event(f"AI: {ai_resp}")

    except Exception as e:
        print(f"[!] LLM Error: {e}")
        ai_resp = "Уучлаарай, алдаа гарлаа."

    # 4. TTS (Chimege)
    print(f"[{session.call_id}] 👄  TTS...")
    output_filename = f"{OUTPUT_FILE_PREFIX}{session.call_id}.wav"
    try:
        h = {"Token": CHIMEGE_TTS_TOKEN, "Content-Type": "text/plain"}
        r = requests.post("https://api.chimege.com/v1.2/synthesize", headers=h, data=ai_resp.encode('utf-8'))
        if r.status_code == 200:
            with open(output_filename, "wb") as f: f.write(r.content)
            
            # Play Audio
            target_ip = RTP_TARGET_IP if RTP_TARGET_IP else session.addr[0]
            # Resolve host.docker.internal if needed
            if target_ip == "host.docker.internal":
                try:
                    target_ip = socket.gethostbyname("host.docker.internal")
                except:
                    print("[!] Could not resolve host.docker.internal")
            
            play_audio(sock, target_ip, session.client_rtp_port, session, output_filename)
            
            # Post-Audio Actions
            if should_transfer:
                print(f"[*] Should Transfer to {OPERATOR_EXT}")
                pass 
            elif should_hangup:
                print(f"[*] Should Hangup")
                pass
                
        else:
            print(f"[!] TTS Error: {r.text}")
    except Exception as e:
        print(f"[!] TTS Exception: {e}")

    session.state = CallState.LISTENING
    print(f"[{session.call_id}] State reset to LISTENING")



# --- СҮЛЖЭЭНИЙ ЛУУПУУД ---
def rtp_loop(rtp_sock, sip_sock):
    print(f"[*] RTP Сонсогч {BIND_IP}:{RTP_PORT} дээр эхэллээ")
    
    last_heartbeat = time.time()
    session_found_count = 0

    while True:
        try:
            data, addr = rtp_sock.recvfrom(4096)
            # IP-ээр сессийг олох (энгийн байдлаар 1 IP = 1 дуудлага гэж үзье)
            # Бодит NAT орчинд RTP порт нь SIP портоос ялгаатай байж болно.
            # Бид RTP эх үүсвэрийг Сесстэй холбох хэрэгтэй.
            
            # Энгийн хайлт: IP таарч байгаа эсэхийг шалгах
            session = None
            with sessions_lock:
                # 1. Яг таарсан IP-г хайх
                for s_addr, s in list(sessions.items())[::-1]:
                    if s_addr[0] == addr[0]: # IP таарч байна
                        session = s
                        break
                
                # 2. Нөөц хувилбар: Хэрэв таарахгүй бол, гэхдээ ГАНЦХАН сесс байвал түүнийг ашиглах (NAT/Docker засвар)
                if not session and len(sessions) == 1:
                    session = list(sessions.values())[0]
                    # Сонголттой: Сессийн хаягийг шинэ эх үүсвэр рүү шинэчлэх үү? 
                    # Одоогоор зүгээр л боловсруулахад хангалттай.
            
            if session:
                # print(f"RTP from {addr} -> Session {session.call_id} State: {session.state}")
                if len(data) > 12: # RTP толгой хэсэг байгаа эсэхийг шалгах
                     pass 
                
                # DEBUG: Пакет бүрийг хэвлэж дохио алдагдаж байгаа эсэхийг шалгах
                # if session.rtp_sequence % 50 == 0:
                #     print(f"RTP from {addr} (Alive)") 
                
                audio_data = session.process_rtp_packet(data[12:]) # RTP толгойг алгасах
                if audio_data:
                    print(f"[*] Яриа илэрлээ ({len(audio_data)} байт). Боловсруулж байна...")
                    threading.Thread(target=process_ai, args=(session, audio_data, rtp_sock)).start()
            else:
                # DEBUG: Пакет ирж байгаа ч сесс олдохгүй байгааг шалгах
                if session_found_count % 50 == 0:
                     print(f"RTP from {addr} -> Сесс олдсонгүй")
                session_found_count += 1
                pass
        except Exception as e:
            print(f"[!] RTP Loop Алдаа: {e}")
        
        # Лууп амьд байгааг батлах зүрхний цохилт
        if time.time() - last_heartbeat > 5:
            # print("[*] RTP Loop Alive")
            last_heartbeat = time.time()

def sip_loop(sip_sock, rtp_sock):
    print(f"[*] SIP Сервер {BIND_IP}:{SIP_PORT} дээр эхэллээ")
    while True:
        try:
            data, addr = sip_sock.recvfrom(4096)
            req = data.decode(errors='ignore')
            
            if "INVITE" in req:
                print(f"\n[+] Дуудлага ирлээ: {addr}")
                call_id = get_header(req, "Call-ID")
                print(f"    Call-ID: {call_id}")
                from_hdr = get_header(req, "From")
                caller_id = "Unknown"
                if "sip:" in from_hdr: 
                    caller_id = from_hdr.split("sip:")[1].split("@")[0]
                
                # Сесс байгаа эсэхийг шалгах
                session = None
                with sessions_lock:
                    for s in sessions.values():
                        if s.call_id == call_id:
                            session = s
                            break
                

                if not session:
                    # Энэ IP-ээс хуучин сесс байгаа эсэхийг шалгаж, түүнийг зогсоох
                    old_session_key = None
                    with sessions_lock:
                        for k, s in sessions.items():
                            if k[0] == addr[0]: # Ижил IP
                                old_session_key = k
                                break
                    
                    if old_session_key:
                        print(f"[*] Хуучин сесс {sessions[old_session_key].call_id}-ийг {addr[0]}-ээс зогсоож, шинэ сесс эхлүүлж байна.")
                        sessions[old_session_key].stop()
                        remove_session(old_session_key)

                    session = create_session(addr, call_id, caller_id)
                else:
                    print(f"[*] Хуучин сессийг үргэлжлүүлж байна: {call_id}")
                    # Хаяг өөрчлөгдсөн бол шинэчлэх (NAT rebinding)
                    session.addr = addr
                    with sessions_lock:
                        sessions[addr] = session

                
                sip_sock.sendto(create_response(100, "Trying", req), addr)
                sip_sock.sendto(create_response(180, "Ringing", req, "t"), addr)
                sip_sock.sendto(create_response(200, "OK", req, "t", True), addr)
                
                client_rtp = parse_port(req, addr[1]+2)
                session.client_rtp_port = client_rtp
                
                threading.Thread(target=send_hole_punch, args=(rtp_sock, addr[0], client_rtp, session)).start()
                session.state = CallState.LISTENING
                
            elif "BYE" in req:
                print(f"[-] Дуудлага дууслаа: {addr}")
                sip_sock.sendto(create_response(200, "OK", req), addr)
                remove_session(addr)
                
            elif "REGISTER" in req:
                sip_sock.sendto(create_response(200, "OK", req, "r"), addr)
                
        except Exception as e:
            print(f"[!] SIP Loop Алдаа: {e}")

def run():
    check_license()
    init_db()
    
    sip_sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sip_sock.bind((BIND_IP, SIP_PORT))
    
    rtp_sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    rtp_sock.bind((BIND_IP, RTP_PORT))
    
    # Start RTP Thread
    threading.Thread(target=rtp_loop, args=(rtp_sock, sip_sock), daemon=True).start()
    
    # Run SIP Loop in Main Thread
    sip_loop(sip_sock, rtp_sock)

if __name__ == "__main__":
    run()
