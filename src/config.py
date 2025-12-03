import os
from dotenv import load_dotenv

load_dotenv()

# Сүлжээний тохиргоо
SIP_PORT = 5060
RTP_PORT = 10000
BIND_IP = "0.0.0.0"
SDP_IP = os.getenv("SDP_IP", "127.0.0.1") # SDP дотор зарлах IP хаяг
RTP_TARGET_IP = os.getenv("RTP_TARGET_IP") # RTP илгээх хаягийг хүчээр заах (Docker NAT-д зориулсан)


# API Түлхүүрүүд
CHIMEGE_SST_TOKEN = os.getenv("CHIMEGE_SST_TOKEN")
CHIMEGE_TTS_TOKEN = os.getenv("CHIMEGE_TTS_TOKEN")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")

# Файлууд
INPUT_FILE_PREFIX = "input_"
OUTPUT_FILE_PREFIX = "response_"
DB_FILE = "products.db"
LOG_FILE = "call_logs.txt"

# Аудио тохиргоо
SILENCE_THRESHOLD = 60 # Чимээгүй гэж үзэх босго (RMS)
SILENCE_LIMIT = 1.1    # Чимээгүй байх хугацаа (секунд)
MIN_AUDIO_LEN = 25     # Аудио бичлэгийн хамгийн бага урт (фрейм)

# SIP Тохиргоо
OPERATOR_EXT = "102"   # Операторын дотуур дугаар
