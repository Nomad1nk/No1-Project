import time
import datetime
from .config import SILENCE_THRESHOLD, SILENCE_LIMIT, MIN_AUDIO_LEN
import audioop
import webrtcvad

class CallState:
    IDLE = 0        # Сул зогсолт
    LISTENING = 1   # Сонсож байна
    PROCESSING = 2  # Боловсруулж байна
    SPEAKING = 3    # Ярьж байна

class CallSession:
    def __init__(self, call_id, caller_id, addr):
        self.call_id = call_id
        self.caller_id = caller_id
        self.addr = addr  # (ip, port)
        self.state = CallState.LISTENING # Анхны төлөв: Сонсох
        self.conversation_history = []
        self.audio_buffer = []
        self.silence_start_time = None
        self.rtp_sequence = 0
        self.rtp_timestamp = 0
        self.last_activity = time.time()
        self.client_rtp_port = None
        
        # VAD (Voice Activity Detection - Дуу хоолой таних)
        # Горим 0: Энгийн, 1: Бага хурдтай, 2: Түрэмгий, 3: Маш түрэмгий
        self.vad = webrtcvad.Vad(0) # Оношилгоо: Горим 0 (Мэдрэг)

    def update_activity(self):
        self.last_activity = time.time()

    def process_rtp_packet(self, payload):
        self.update_activity()
        if self.state != CallState.LISTENING:
            return None

        # VAD-д зориулж u-law-г PCM рүү хөрвүүлэх
        try:
            pcm = audioop.ulaw2lin(payload, 2)
        except:
            return None

        # RMS (Дууны хүч) тооцоолох
        rms = audioop.rms(payload, 1)

        # VAD ашиглан яриа эсэхийг шалгах
        try:
            is_speech_vad = self.vad.is_speech(pcm, 8000)
        except:
            is_speech_vad = False

        # Хосолсон шийдвэр: Дуу хоолой БА Чимээнээс чанга байх ёстой
        # is_speech = is_speech_vad and (rms > SILENCE_THRESHOLD)
        
        # НӨӨЦ ХУВИЛБАР: Зөвхөн RMS (VAD заримдаа яриаг танихгүй байсан тул)
        is_speech = (rms > SILENCE_THRESHOLD)
        
        # DEBUG: RMS болон VAD утгуудыг хэвлэх
        # if self.rtp_sequence % 50 == 0:
        #      print(f" [RMS: {rms} | VAD: {'YES' if is_speech_vad else 'NO'} | DECISION: {'YES' if is_speech else 'NO'}]")

        if is_speech:
            self.audio_buffer.append(payload)
            self.silence_start_time = None
            
            if len(self.audio_buffer) % 50 == 0:
                print(f"[*] Бичиж байна... {len(self.audio_buffer)} фрейм (RMS: {rms})")
            
            # Аюулгүйн хавхлага: 10 секундын хязгаар
            if len(self.audio_buffer) > 500:
                print(f"[*] Дээд хязгаарт хүрсэн тул албадан боловсруулж байна.")
                audio_data = b''.join(self.audio_buffer)
                self.audio_buffer = []
                self.silence_start_time = None
                self.state = CallState.PROCESSING
                return audio_data

        else:
            # Чимээгүй үе
            if len(self.audio_buffer) > 0:
                if self.silence_start_time is None:
                    self.silence_start_time = time.time()
                elif (time.time() - self.silence_start_time) > SILENCE_LIMIT:
                    if len(self.audio_buffer) > MIN_AUDIO_LEN:
                        print(f"[*] Чимээгүй боллоо (VAD). {len(self.audio_buffer)} фрейм боловсруулж байна.")
                        audio_data = b''.join(self.audio_buffer)
                        self.audio_buffer = []
                        self.silence_start_time = None
                        self.state = CallState.PROCESSING
                        return audio_data
                    else:
                        # Хэт богино (чимээний огцом өсөлт), буферийг цэвэрлэх
                        self.audio_buffer = []
                        self.silence_start_time = None
        return None

    def stop(self):
        self.state = CallState.IDLE
        self.audio_buffer = []
        print(f"[*] Сесс {self.call_id} зогслоо.")
