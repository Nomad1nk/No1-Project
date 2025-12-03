import struct
import time
import audioop
import wave
from .session import CallState

def send_hole_punch(sock, target_ip, target_port, session):
    silence = b'\xff' * 160
    for i in range(50):
        hdr = struct.pack('!BBHII', 0x80, 0, session.rtp_sequence, session.rtp_timestamp, 12345)
        sock.sendto(hdr + silence, (target_ip, target_port))
        session.rtp_sequence += 1
        session.rtp_timestamp += 160
        time.sleep(0.02)

def play_audio(sock, target_ip, target_port, session, filename):
    session.state = CallState.SPEAKING
    print(f"[*] 🔊 Playing {filename} to {target_ip}:{target_port}")
    
    try:
        with wave.open(filename, 'rb') as wf:
            content = wf.readframes(wf.getnframes())
            rate = wf.getframerate()
            width = wf.getsampwidth()
            channels = wf.getnchannels()
            
            if rate != 8000: 
                content, _ = audioop.ratecv(content, width, channels, rate, 8000, None)
            if channels == 2: 
                content = audioop.tomono(content, width, 0.5, 0.5)
                
            offset = 0
            while offset < len(content) and session.state == CallState.SPEAKING:
                chunk = content[offset:offset+320] # 320 bytes = 160 samples * 2 bytes (16bit) -> convert to ulaw
                offset += 320
                
                # Convert linear to ulaw (PCMU)
                ulaw_chunk = audioop.lin2ulaw(chunk, 2)
                
                if len(ulaw_chunk) < 160: 
                    ulaw_chunk += b'\xff' * (160 - len(ulaw_chunk))
                
                hdr = struct.pack('!BBHII', 0x80, 0, session.rtp_sequence, session.rtp_timestamp, 12345)
                
                # 1. Send to User's LAN IP (So they hear it)
                sock.sendto(hdr + ulaw_chunk, (target_ip, target_port))
                
                # 2. Send to Docker Gateway (To keep NAT alive)
                if session.addr and session.addr[0] != target_ip:
                    try:
                        sock.sendto(hdr + ulaw_chunk, session.addr)
                    except: pass
                
                session.rtp_sequence += 1
                session.rtp_timestamp += 160
                time.sleep(0.02)
    except Exception as e:
        print(f"[!] RTP Error: {e}")
        
    if session.state == CallState.SPEAKING:
        session.state = CallState.LISTENING
