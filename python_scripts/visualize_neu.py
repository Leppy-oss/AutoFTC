import cadquery as cq
import trimesh
import json
from cadquery import exporters

# === Config ===
STEP_FILE = "1101_Series_U-Beam_17_Hole_136mm_Length.STEP"
METADATA_FILE = "mesh_metadata.json"


# === Step 1: Load STEP file using CadQuery ===
shape = cq.importers.importStep(STEP_FILE)
solid = shape.val()  # Get the actual Shape object from Workplane/Compound


# === Step 2: Export to a temporary STL (CadQuery → mesh) ===
exporters.export(solid, "temp.stl")  # Use STL since trimesh handles it well

# === Step 3: Load STL into Trimesh ===
mesh = trimesh.load("temp.stl")


# === Step 4: Extract and Print Metadata ===
metadata = {
    "bounding_box": mesh.bounding_box.extents.tolist(),
    "bounding_box_center": mesh.bounding_box.centroid.tolist(),
    "volume": mesh.volume,
    "surface_area": mesh.area,
    "vertices": len(mesh.vertices),
    "faces": len(mesh.faces),
}

# Save metadata to JSON
with open(METADATA_FILE, "w") as f:
    json.dump(metadata, f, indent=4)

print("✅ Metadata saved:", METADATA_FILE)
print(json.dumps(metadata, indent=4))


# === Step 5: Visualize in Trimesh Viewer ===
mesh.show()
