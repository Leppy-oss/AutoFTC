import os
import re

FOLDER_PATH = "./models"

for filename in os.listdir(FOLDER_PATH):
    if filename.endswith(".STEP"):
        new_name = None

        # Grid-style holes (e.g. Grid_Plate_3_x_5_Hole)
        match_grid = re.match(
            r"^\d{4}_Series_([A-Za-z\-_]+)_(\d+)_x_(\d+)_Hole.*\.STEP$", filename
        )

        # Single hole count (e.g. U-Beam_3_Hole)
        match_single = re.match(
            r"^\d{4}_Series_([A-Za-z\-_]+)_(\d+)_Hole.*\.STEP$", filename
        )

        # Spacer with only length
        match_spacer_len = re.match(
            r"^\d{4}_Series_\d+mm_OD_([A-Za-z\-_]+)_(\d+(?:\.\d+)?)mm.*\.STEP$",
            filename,
        )

        # Spacer with ID, OD, and Length
        match_spacer_full = re.match(
            r"^\d{4}_Series_(\d+(?:\.\d+)?)mm_ID_([A-Za-z\-_]+)_(\d+(?:\.\d+)?)mm_OD_(\d+(?:\.\d+)?)mm.*\.STEP$",
            filename,
        )

        # Gears: e.g. Aluminum_MOD_0.8_Hub_Mount_Gear_14mm_Bore_48_Tooth
        match_gear = re.match(
            r"^\d{4}_Series_.*?_(Hub[_\-]Mount[_\-]Gear).*?_(\d+)_Tooth.*\.STEP$",
            filename,
        )
        # Gear with possible spline teeth (e.g. Servo_Gear_25_Tooth_Spline_15_Tooth)
        match_gear_spline = re.search(
            r"_((?:Servo|Pinion|Hub[-_]Mount|Face[-_]Mount))[-_]Gear[_\w]*_(\d+)_Tooth(?:_Spline_(\d+)_Tooth)?",
            filename,
            re.IGNORECASE,
        )

        if match_grid:
            part_name_raw, row, col = match_grid.groups()
            part_chunks = re.split(r"[-_]", part_name_raw)
            part_name = "".join(chunk.capitalize() for chunk in part_chunks)
            new_name = f"{part_name}{row}x{col}H.STEP"

        elif match_single:
            part_name_raw, hole_count = match_single.groups()
            part_chunks = re.split(r"[-_]", part_name_raw)
            part_name = "".join(chunk.capitalize() for chunk in part_chunks)
            new_name = f"{part_name}{hole_count}H.STEP"

        elif match_spacer_full:
            id_val, part_name_raw, od_val, length = match_spacer_full.groups()
            part_chunks = re.split(r"[-_]", part_name_raw)
            part_name = "".join(chunk.capitalize() for chunk in part_chunks)
            new_name = f"{part_name}{id_val}ID{od_val}OD{length}.STEP"

        elif match_spacer_len:
            part_name_raw, length = match_spacer_len.groups()
            part_chunks = re.split(r"[-_]", part_name_raw)
            part_name = "".join(chunk.capitalize() for chunk in part_chunks)
            new_name = f"{part_name}{length}.STEP"

        elif match_gear:
            part_name_raw, tooth_count = match_gear.groups()
            part_chunks = re.split(r"[-_]", part_name_raw)
            part_name = "".join(chunk.capitalize() for chunk in part_chunks)
            new_name = f"{part_name}{tooth_count}T.STEP"

        elif match_gear_spline:
            gear_type_raw, gear_tooth_count, spline_tooth_count = (
                match_gear_spline.groups()
            )
            part_chunks = re.split(r"[-_]", gear_type_raw)
            gear_type = "".join(chunk.capitalize() for chunk in part_chunks) + "Gear"
            tooth_count = spline_tooth_count if spline_tooth_count else gear_tooth_count
            new_name = f"{gear_type}{tooth_count}T.STEP"

        if new_name:
            old_path = os.path.join(FOLDER_PATH, filename)
            new_path = os.path.join(FOLDER_PATH, new_name)

            print(f"Renaming: {filename} → {new_name}")
            os.rename(old_path, new_path)
        else:
            print(f"Skipped: {filename} (pattern not matched)")
