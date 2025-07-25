# Xernl

## Description
Xernl is a Windows information grabber written in Python. It collects sensitive data such as cookies, passwords, tokens, and more from various browsers (including Chrome, Edge, Brave, Yandex, and Zen) and sends them to a remote server or webhook.

**For educational and authorized testing purposes only.**

## Features
- Extracts cookies (including session/auth cookies like .ROBLOSECURITY) from Chromium-based browsers and Zen
- Grabs saved passwords, autofill data, and browsing history
- Supports multiple browser profiles
- Decrypts Chrome/Chromium cookies using the correct master key
- Sends data to a Discord webhook
- Includes a batch script to build the project into a standalone executable

## Build Instructions
1. Make sure you have Python 3.8+ installed
2. Install dependencies:
   ```sh
   pip install -r requirements.txt
   ```
3. Build the executable (Windows only):
   ```sh
   build.bat
   ```
   The executable will be created in the `dist` folder as `Xernl.exe`.

## Usage
- Edit `main.py` to set your Discord webhook URL
- Run the script directly with Python, or use the built executable

## Disclaimer
This tool is for educational and authorized testing only. Unauthorized use is illegal and unethical.
