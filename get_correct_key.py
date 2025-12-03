import hashlib
import hmac

SECRET_KEY = b"BEDEL_AI_SUPER_SECRET_KEY_2025"
MAC = "02:42:AC:11:00:02"

signature = hmac.new(SECRET_KEY, MAC.encode(), hashlib.sha256).hexdigest()
key = signature[:16].upper()
print(f"CORRECT_KEY={'-'.join(key[i:i+4] for i in range(0, 16, 4))}")
