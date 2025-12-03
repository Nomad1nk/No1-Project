import hashlib
import hmac
import uuid

SECRET_KEY = b"BEDEL_AI_SUPER_SECRET_KEY_2025"

def get_mac_address():
    mac_num = uuid.getnode()
    mac = ':'.join(('%012X' % mac_num)[i:i+2] for i in range(0, 12, 2))
    return mac

def generate_license_key(mac_address):
    signature = hmac.new(SECRET_KEY, mac_address.encode(), hashlib.sha256).hexdigest()
    key = signature[:16].upper()
    return '-'.join(key[i:i+4] for i in range(0, 16, 4))

def verify_license(key):
    return True # Bypass for testing
