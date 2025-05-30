import cadquery as cq
import trimesh
import numpy as np
from pathlib import Path


# Load STEP file
def load_step(filepath):
    shape = cq.importers.importStep(str(filepath))
    return shape


# Convert to mesh and export .glb
def export_to_glb(shape, out_path):
    mesh = shape.toCompound().tessellate(0.1)
    vertices = np.array([v.toTuple() for v in mesh[0]])
    faces = np.array(mesh[1])

    # Create trimesh for analysis
    tri = trimesh.Trimesh(vertices=vertices, faces=faces, process=True)
    tri.export(out_path.with_suffix(".glb"))

    return tri


# Extract metadata
def get_metadata(mesh: trimesh.Trimesh):
    return {
        "bounding_box": mesh.bounding_box.extents.tolist(),
        "volume": mesh.volume,
        "surface_area": mesh.area,
        "centroid": mesh.centroid.tolist(),
        "num_faces": len(mesh.faces),
        "num_vertices": len(mesh.vertices),
    }


# Optional visualization
def visualize(mesh: trimesh.Trimesh):
    mesh.show()


# Main
def process_step(filepath):
    step_path = Path(filepath)
    out_glb = step_path.with_suffix(".glb")

    shape = load_step(step_path)
    mesh = export_to_glb(shape, out_glb)

    metadata = get_metadata(mesh)
    visualize(mesh)

    # Save metadata
    metadata_path = step_path.with_suffix(".json")
    with open(metadata_path, "w") as f:
        import json

        json.dump(metadata, f, indent=2)

    print(f"Exported: {out_glb}")
    print(f"Metadata: {metadata_path}")
    return metadata


# Example
process_step("1101_Series_U-Beam_17_Hole_136mm_Length.STEP")
