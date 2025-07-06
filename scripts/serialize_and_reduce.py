import wx
import os
import json
import glob

from OCC.Core.STEPControl import STEPControl_Reader
from OCC.Core.BRepBndLib import brepbndlib
from OCC.Core.Bnd import Bnd_Box
from OCC.Core.BRepPrimAPI import BRepPrimAPI_MakeSphere
from OCC.Core.TopExp import TopExp_Explorer
from OCC.Core.TopAbs import TopAbs_FACE
from OCC.Core.GProp import GProp_GProps
from OCC.Core.BRepGProp import brepgprop
from OCC.Display.SimpleGui import init_display
from OCC.Core.gp import gp_Pnt
from OCC.Core.BRepAdaptor import BRepAdaptor_Surface
from OCC.Core.GeomAbs import GeomAbs_Cylinder, GeomAbs_Plane
from OCC.Core.IFSelect import IFSelect_RetDone
from OCC.Extend.DataExchange import write_gltf_file
from OCC.Core.TopoDS import topods
from OCC.Core.AIS import AIS_Shape

from OCC.Core.BRepClass3d import BRepClass3d_SolidClassifier
from OCC.Core.TopAbs import TopAbs_OUT
from OCC.Core.BRepAdaptor import BRepAdaptor_Surface
from OCC.Core.gp import gp_Pnt, gp_Vec
from OCC.Core.GeomLProp import GeomLProp_SLProps
import open3d as o3d

MODELS_DIR = "./models"
GLB_DIR = "./glb"
SERIALIZED_DIR = "./serialized"

os.makedirs(GLB_DIR, exist_ok=True)
os.makedirs(SERIALIZED_DIR, exist_ok=True)


def get_bounding_box(shape):
    bbox = Bnd_Box()
    brepbndlib.Add(shape, bbox)
    xmin, ymin, zmin, xmax, ymax, zmax = bbox.Get()
    center = [round(v, 2) for v in [(xmin + xmax) / 2, (ymin + ymax) / 2, (zmin + zmax) / 2]]
    size = [round(v, 2) for v in [xmax - xmin, ymax - ymin, zmax - zmin]]
    return {
        "size": size,
        "center": center,
    }

def simplify_glb(path, target_triangles_ratio=0.5):
    print(f"Loading GLB for simplification: {path}")
    mesh = o3d.io.read_triangle_mesh(path, enable_post_processing=True)
    if mesh.is_empty():
        raise Exception(f"Failed to load mesh from {path}")

    orig_triangles = len(mesh.triangles)
    target_triangles = int(orig_triangles * target_triangles_ratio)
    print(f"Original triangles: {orig_triangles}, target: {target_triangles}")

    if orig_triangles < 30000:
        print("Too few original triangles, will not decimate")
        return
    
    if orig_triangles < 50000:
        target_triangles_ratio = 0.6

    os.remove(path)
    simplified_mesh = mesh.simplify_quadric_decimation(target_triangles)

    # Clean up errors
    simplified_mesh.remove_duplicated_vertices()
    simplified_mesh.remove_duplicated_triangles()
    simplified_mesh.remove_degenerate_triangles()
    simplified_mesh.remove_non_manifold_edges()
    simplified_mesh.compute_vertex_normals()

    print(f"Simplified triangles: {len(simplified_mesh.triangles)}")

    o3d.io.write_triangle_mesh(path, simplified_mesh)
    print(f"Simplified GLB saved: {path}")


def process_step_file(filepath):
    filename = os.path.basename(filepath)
    part_id = os.path.splitext(filename)[0]
    print(f"Processing {filename}...")

    reader = STEPControl_Reader()
    status = reader.ReadFile(filepath)
    if status != IFSelect_RetDone:
        print(f"Error reading {filename}")
        return

    reader.TransferRoots()
    shape = reader.OneShape()

    print(f"Loaded {filename}. Retrieving bounding box information...")
    bbox_info = get_bounding_box(shape)

    data = {
        "pid": part_id,
        "bs": bbox_info["size"],
        "bc": bbox_info["center"],
    }

    with open(os.path.join(SERIALIZED_DIR, part_id + ".json"), "w") as f:
        json.dump(data, f, indent=4)

    # Export original glb
    glb_path = os.path.join(GLB_DIR, part_id + ".glb")
    write_gltf_file(shape, glb_path, binary=True)
    print(f"Saved GLB: {glb_path}")

    # Export simplified glb (if necessary)
    simplify_glb(glb_path)


if __name__ == "__main__":
    step_files = glob.glob(os.path.join(MODELS_DIR, "*.step")) + glob.glob(
        os.path.join(MODELS_DIR, "*.STEP")
    )

    for filepath in step_files:
        process_step_file(filepath)
