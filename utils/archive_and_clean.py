import os
import shutil
from datetime import datetime

base_dir = r"c:\Users\ACER\Desktop\a-z-hacettepe\hacettepe_ia_pipeline"
archive_base = os.path.join(base_dir, "archive")
os.makedirs(archive_base, exist_ok=True)

ts = datetime.now().strftime("%Y%m%d_%H%M%S")
target_dir = os.path.join(archive_base, ts)
os.makedirs(target_dir, exist_ok=True)

# Files to move
files_to_move = [
    os.path.join(base_dir, "inputs", "az_links.json"),
    os.path.join(base_dir, "hybrid_master.json")
]

# Move output_*.json from base_dir
for f in os.listdir(base_dir):
    if f.startswith("output_") and f.endswith(".json"):
        files_to_move.append(os.path.join(base_dir, f))

# Move contents of outputs/ directory
outputs_dir = os.path.join(base_dir, "outputs")
if os.path.exists(outputs_dir):
    for f in os.listdir(outputs_dir):
        files_to_move.append(os.path.join(outputs_dir, f))

for fpath in files_to_move:
    if os.path.exists(fpath):
        try:
            shutil.move(fpath, target_dir)
            print(f"Moved: {fpath}")
        except Exception as e:
            print(f"Error moving {fpath}: {e}")

print(f"Archive created at: {target_dir}")
