import os
import re

FOLDER_PATH = "./models"

for filename in os.listdir(FOLDER_PATH):
    if filename.endswith(".STEP"):
        # match pattern *N*ODx*N*Standoff
        match = re.match(r"^(.*)ODx(.*)Standoff.STEP", filename)
        if match:
            od_value, standoff_value = match.groups()
            new_name = f"Standoff{standoff_value}.STEP"

            old_path = os.path.join(FOLDER_PATH, filename)
            new_path = os.path.join(FOLDER_PATH, new_name)

            print(f"Renaming: {filename} → {new_name}")
            os.rename(old_path, new_path)
        else:
            print(f"Skipped: {filename} (pattern not matched)")
