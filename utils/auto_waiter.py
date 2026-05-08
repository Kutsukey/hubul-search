import time
import os
import psutil
import json
import subprocess

TARGET_SCRIPT = "hybrid_hacettepe_crawler_3.py"

def is_crawler_running():
    for proc in psutil.process_iter(['name', 'cmdline']):
        try:
            if proc.info['name'] == 'python.exe' and proc.info['cmdline']:
                cmd = " ".join(proc.info['cmdline'])
                if TARGET_SCRIPT in cmd and "auto_waiter" not in cmd:
                    return True
        except:
            pass
    return False

print("Waiting for initial crawler to finish...")
while is_crawler_running():
    time.sleep(30)

print("Crawler finished. Processing timeouts...")
processed_file = r"c:\Users\ACER\Desktop\a-z-hacettepe\hacettepe_ia_pipeline\outputs\processed_urls.json"
try:
    with open(processed_file, "r", encoding="utf-8") as f:
        data = json.load(f)
    
    # Remove timeouts
    new_data = {k: v for k, v in data.items() if "Timeout" not in v}
    removed_count = len(data) - len(new_data)
    
    with open(processed_file, "w", encoding="utf-8") as f:
        json.dump(new_data, f, ensure_ascii=False, indent=4)
        
    print(f"Removed {removed_count} timeout entries.")
    
    if removed_count > 0:
        print("Restarting crawler for timeouts...")
        subprocess.run([r"c:\Users\ACER\Desktop\a-z-hacettepe\crawl_venv\Scripts\python.exe", TARGET_SCRIPT], cwd=r"c:\Users\ACER\Desktop\a-z-hacettepe\hacettepe_ia_pipeline")
        
except Exception as e:
    print(f"Error: {e}")

print("All done!")
