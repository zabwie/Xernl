import os
import platform
import socket
import uuid
import psutil
import json
import subprocess
from datetime import datetime

def get_system_info(output_folder):
    """Collect detailed system information"""
    system_folder = os.path.join(output_folder, "system_info")
    os.makedirs(system_folder, exist_ok=True)
    output_file = os.path.join(system_folder, "system_details.json")
    
    system_data = {}
    
    # Basic system info
    system_data["hostname"] = socket.gethostname()
    system_data["os"] = {
        "system": platform.system(),
        "release": platform.release(),
        "version": platform.version(),
        "architecture": platform.machine(),
        "processor": platform.processor()
    }
    
    # Network info
    try:
        system_data["network"] = {
            "ip_address": socket.gethostbyname(socket.gethostname()),
            "mac_address": ':'.join(['{:02x}'.format((uuid.getnode() >> elements) & 0xff) 
                                for elements in range(0, 48, 8)][::-1])
        }
    except Exception as e:
        system_data["network"] = {"error": str(e)}
    
    # Hardware info
    try:
        system_data["hardware"] = {
            "cpu_cores": psutil.cpu_count(logical=False),
            "cpu_threads": psutil.cpu_count(logical=True),
            "ram_total_gb": round(psutil.virtual_memory().total / (1024**3), 2),
            "ram_available_gb": round(psutil.virtual_memory().available / (1024**3), 2)
        }
    except Exception as e:
        system_data["hardware"] = {"error": str(e)}
    
    # Disk info with better error handling
    system_data["disks"] = []
    for partition in psutil.disk_partitions(all=False):
        try:
            # Skip CD-ROM drives and network drives
            if partition.fstype == '' or 'cdrom' in partition.opts.lower() or not os.path.exists(partition.mountpoint):
                continue
                
            usage = psutil.disk_usage(partition.mountpoint)
            system_data["disks"].append({
                "device": partition.device,
                "mountpoint": partition.mountpoint,
                "fstype": partition.fstype,
                "total_gb": round(usage.total / (1024**3), 2),
                "used_gb": round(usage.used / (1024**3), 2),
                "free_gb": round(usage.free / (1024**3), 2),
                "percent_used": usage.percent
            })
        except Exception as e:
            # Just log the error and continue with next partition
            system_data["disks"].append({
                "device": partition.device,
                "mountpoint": partition.mountpoint,
                "fstype": partition.fstype,
                "error": str(e)
            })
    
    # Get installed software using WMI
    try:
        system_data["installed_software"] = []
        # Use a more reliable method to get installed software
        cmd = 'powershell "Get-ItemProperty HKLM:\\Software\\Wow6432Node\\Microsoft\\Windows\\CurrentVersion\\Uninstall\\* | Select-Object DisplayName, DisplayVersion, Publisher, InstallDate | ConvertTo-Json"'
        process = subprocess.Popen(cmd, shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        stdout, stderr = process.communicate()
        
        if stdout:
            try:
                software_list = json.loads(stdout.decode('utf-8', errors='ignore'))
                # Handle case where only one item is returned (not in a list)
                if isinstance(software_list, dict):
                    software_list = [software_list]
                    
                for software in software_list:
                    if software.get('DisplayName'):
                        system_data["installed_software"].append({
                            "name": software.get('DisplayName', ''),
                            "version": software.get('DisplayVersion', ''),
                            "vendor": software.get('Publisher', ''),
                            "install_date": software.get('InstallDate', '')
                        })
            except json.JSONDecodeError:
                system_data["installed_software_error"] = "Failed to parse software list"
    except Exception as e:
        system_data["installed_software_error"] = str(e)
    
    # Get running processes with better error handling
    system_data["running_processes"] = []
    for proc in psutil.process_iter(['pid', 'name', 'username', 'memory_info']):
        try:
            process_info = proc.info
            if process_info['name'] and process_info['pid']:  # Only include processes with valid name and PID
                system_data["running_processes"].append({
                    "pid": process_info['pid'],
                    "name": process_info['name'],
                    "username": process_info.get('username', 'N/A'),
                    "memory_mb": round(process_info['memory_info'].rss / (1024**2), 2) if process_info.get('memory_info') else None
                })
        except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess, AttributeError):
            # Skip processes that can't be accessed
            continue
    
    # Get system uptime
    try:
        system_data["uptime_seconds"] = int(psutil.boot_time())
        system_data["uptime_readable"] = str(datetime.now() - datetime.fromtimestamp(psutil.boot_time()))
    except Exception as e:
        system_data["uptime_error"] = str(e)
    
    # Save to JSON
    with open(output_file, 'w') as f:
        json.dump(system_data, f, indent=4)
    
    print(f"[+] System information saved to {output_file}")
    return True

def get_installed_browsers(output_folder):
    """Detect installed browsers on the system"""
    browsers_folder = os.path.join(output_folder, "browsers")
    os.makedirs(browsers_folder, exist_ok=True)
    output_file = os.path.join(browsers_folder, "installed_browsers.json")
    
    browser_paths = {
        "chrome": [
            r"C:\Program Files\Google\Chrome\Application\chrome.exe",
            r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe"
        ],
        "firefox": [
            r"C:\Program Files\Mozilla Firefox\firefox.exe",
            r"C:\Program Files (x86)\Mozilla Firefox\firefox.exe"
        ],
        "edge": [
            r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe",
            r"C:\Program Files\Microsoft\Edge\Application\msedge.exe"
        ],
        "opera": [
            r"C:\Program Files\Opera\launcher.exe",
            r"C:\Program Files (x86)\Opera\launcher.exe"
        ],
        "brave": [
            r"C:\Program Files\BraveSoftware\Brave-Browser\Application\brave.exe",
            r"C:\Program Files (x86)\BraveSoftware\Brave-Browser\Application\brave.exe"
        ]
    }
    
    installed_browsers = {}
    
    for browser, paths in browser_paths.items():
        for path in paths:
            if os.path.exists(path):
                installed_browsers[browser] = path
                break
    
    # Save to JSON
    with open(output_file, 'w') as f:
        json.dump(installed_browsers, f, indent=4)
    
    print(f"[+] Installed browsers information saved to {output_file}")
    return installed_browsers