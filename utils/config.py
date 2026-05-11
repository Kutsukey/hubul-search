import os

# Project root directory
# Assuming this file is in utils/config.py, its parent is utils/ and its parent is root.
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# Input directories
INPUTS_DIR = os.path.join(BASE_DIR, "inputs")
SEED_JSON = os.path.join(INPUTS_DIR, "seed_urls.json")
AZ_LINKS_JSON = os.path.join(INPUTS_DIR, "az_links.json")

# Output directories (Live data for widget)
# We use public/outputs/ as the source of truth for the frontend
OUTPUTS_DIR = os.path.join(BASE_DIR, "public", "outputs")
MASTER_JSON = os.path.join(OUTPUTS_DIR, "hybrid_master.json")
ANNOUNCEMENTS_JSON = os.path.join(OUTPUTS_DIR, "announcements_live.json")
POTENTIAL_NEW_JSON = os.path.join(OUTPUTS_DIR, "potential_new_sites.json")
PROCESSED_URLS_JSON = os.path.join(OUTPUTS_DIR, "processed_urls.json")

# Ensure directories exist
os.makedirs(INPUTS_DIR, exist_ok=True)
os.makedirs(OUTPUTS_DIR, exist_ok=True)

print(f"[Config] ROOT: {BASE_DIR}")
print(f"[Config] INPUTS: {INPUTS_DIR}")
print(f"[Config] OUTPUTS: {OUTPUTS_DIR}")
