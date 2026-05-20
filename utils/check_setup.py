import os
import sys
import io
import json

# Windows Console UTF-8 Fix
if sys.platform == "win32":
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

# Ensure we can load dotenv
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    print("[!] Warning: python-dotenv not installed. Environment variables might not load from .env file.")

print("🔍 Starting Hubul Search Setup and Configuration Verification...\n")

errors = 0
warnings = 0

# 1. Check Python Dependencies
dependencies = [
    ("aiohttp", "aiohttp"),
    ("bs4", "beautifulsoup4"),
    ("requests", "requests"),
    ("urllib3", "urllib3"),
    ("pydantic", "pydantic"),
    ("crawl4ai", "crawl4ai"),
    ("playwright", "playwright"),
    ("google.genai", "google-genai"),
]

print("📦 Checking Python Dependencies:")
for module_name, pip_name in dependencies:
    try:
        __import__(module_name)
        print(f"  [✓] {pip_name} is installed.")
    except ImportError as e:
        print(f"  [X] {pip_name} is MISSING! (Error: {e})")
        errors += 1

# 2. Check File & Directory Structure
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

required_dirs = [
    ("inputs", os.path.join(BASE_DIR, "inputs")),
    ("public/outputs", os.path.join(BASE_DIR, "public", "outputs")),
]

required_files = [
    ("inputs/seed_urls.json", os.path.join(BASE_DIR, "inputs", "seed_urls.json")),
    ("public/ia-widget.js", os.path.join(BASE_DIR, "public", "ia-widget.js")),
    ("public/index.html", os.path.join(BASE_DIR, "public", "index.html")),
    ("requirements.txt", os.path.join(BASE_DIR, "requirements.txt")),
]

print("\n📁 Checking Project Directory & File Structure:")
for name, path in required_dirs:
    if os.path.isdir(path):
        print(f"  [✓] Directory '{name}' exists.")
    else:
        print(f"  [X] Directory '{name}' is MISSING at {path}")
        errors += 1

for name, path in required_files:
    if os.path.isfile(path):
        print(f"  [✓] File '{name}' exists.")
    else:
        print(f"  [X] File '{name}' is MISSING at {path}")
        errors += 1

# 3. Check Google API Key
print("\n🔑 Checking Google GenAI Configuration:")
api_key = os.getenv("GOOGLE_API_KEY")

if not api_key:
    print("  [X] GOOGLE_API_KEY environment variable is NOT set!")
    errors += 1
else:
    print("  [✓] GOOGLE_API_KEY environment variable is set. Verifying API key validity...")
    try:
        from google import genai
        # Initialize client with explicitly provided key
        client = genai.Client(api_key=api_key)
        # Test connection using gemini-2.5-flash (safe, standard, cheap/fast model)
        response = client.models.generate_content(
            model="gemini-2.5-flash",
            contents="Say 'OK' if you can read this."
        )
        if response.text:
            print(f"  [✓] Google API Connection successful! Test response: {response.text.strip()}")
        else:
            print("  [X] Google API call returned an empty response.")
            errors += 1
    except Exception as e:
        print(f"  [X] Google API Verification failed! Error: {e}")
        errors += 1

# 4. Check Supabase Telemetry Configuration
print("\n📡 Checking Supabase Telemetry Configuration:")
widget_path = os.path.join(BASE_DIR, "public", "ia-widget.js")
index_path = os.path.join(BASE_DIR, "public", "index.html")

supabase_configs = {}

def extract_supabase_details(filepath, label):
    global warnings
    if not os.path.isfile(filepath):
        return None
    url, key = None, None
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            for line in f:
                if "const SUPABASE_URL" in line:
                    parts = line.split("=")
                    if len(parts) > 1:
                        url = parts[1].strip().strip('";').strip("'")
                if "const SUPABASE_ANON_KEY" in line:
                    parts = line.split("=")
                    if len(parts) > 1:
                        key = parts[1].strip().strip('";').strip("'")
        
        if url and key:
            print(f"  [✓] Supabase credentials found in '{label}'")
            # Check for defaults
            if "ksishnnumgdmouinmsfq" in url:
                print(f"  [!] Warning: '{label}' is using the default/template Supabase database (ksishnnumgdmouinmsfq).")
                print("      Please set up your own database on supabase.com and update the values in the files.")
                warnings += 1
            return {"url": url, "key": key}
        else:
            print(f"  [!] Warning: Could not parse Supabase credentials from '{label}'.")
            warnings += 1
    except Exception as e:
        print(f"  [!] Warning: Error reading '{label}': {e}")
        warnings += 1
    return None

supabase_configs["ia-widget.js"] = extract_supabase_details(widget_path, "public/ia-widget.js")
supabase_configs["index.html"] = extract_supabase_details(index_path, "public/index.html")

# Try to reach the Supabase endpoint if configured
target_config = supabase_configs.get("ia-widget.js") or supabase_configs.get("index.html")
if target_config and target_config.get("url"):
    sb_url = target_config["url"]
    sb_key = target_config["key"]
    print(f"  Testing connection to Supabase endpoint: {sb_url}")
    try:
        import requests
        # Run a query against search_logs table
        headers = {
            "apikey": sb_key,
            "Authorization": f"Bearer {sb_key}"
        }
        test_url = f"{sb_url}/rest/v1/search_logs?select=id&limit=1"
        res = requests.get(test_url, headers=headers, timeout=10)
        if res.status_code in [200, 201]:
            print("  [✓] Connection to Supabase database successful! Table 'search_logs' is accessible.")
        elif res.status_code == 404:
            print(f"  [X] Connection succeeded, but returned HTTP {res.status_code}. Table 'search_logs' may not exist in your Supabase database.")
            errors += 1
        else:
            print(f"  [X] Connection failed with HTTP status code: {res.status_code}")
            print(f"      Response: {res.text}")
            errors += 1
    except Exception as e:
        print(f"  [X] Connection test to Supabase failed! Error: {e}")
        errors += 1

# 5. Final Report
print("\n📋 Verification Summary:")
print(f"  Total Errors  : {errors}")
print(f"  Total Warnings: {warnings}")

if errors > 0:
    print("\n❌ Setup Verification FAILED. Please resolve the errors listed above.")
    sys.exit(1)
else:
    print("\n✅ Setup Verification PASSED! Everything is correctly configured.")
    sys.exit(0)
