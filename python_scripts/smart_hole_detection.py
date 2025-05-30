import os
import json
import cadquery as cq
from cadquery import exporters
import numpy as np
import trimesh
import open3d as o3d
from OCC.Core.BRepAdaptor import BRepAdaptor_Surface
from OCC.Core.GeomAbs import GeomAbs_Cylinder

# Directories
MODEL_DIR = "./models"
GLB_DIR = "./gbl"
JSON_DIR = "./serialized_models"
TEMP_STL = "./temp.stl"

os.makedirs(GLB_DIR, exist_ok=True)
os.makedirs(JSON_DIR, exist_ok=True)


def is_cylindrical(face):
    surf = BRepAdaptor_Surface(face.wrapped)
    return surf.GetType() == GeomAbs_Cylinder


def get_cylinder_info(face):
    surf = BRepAdaptor_Surface(face.wrapped)
    loc = surf.Axis().Location()
    dir = surf.Axis().Direction()
    radius = surf.Cylinder().Radius()
    center = (loc.X(), loc.Y(), loc.Z())
    direction = (dir.X(), dir.Y(), dir.Z())
    return center, direction, radius * 2  # diameter


def deduplicate_axes(attachment_points, tolerance=0.1):
    seen = []
    unique = []
    for pt in attachment_points:
        axis = np.round(np.array(pt["center"] + pt["direction"]), 3)
        duplicate = False
        for s in seen:
            if np.linalg.norm(axis - s) < tolerance:
                duplicate = True
                break
        if not duplicate:
            seen.append(axis)
            unique.append(pt)
    return unique


def detect_attachment_points(solid, min_diameter=4.0):
    attachment_points = []
    for face in solid.faces().vals():
        if is_cylindrical(face):
            center, direction, diameter = get_cylinder_info(face)
            if diameter >= min_diameter:
                attachment_points.append(
                    {"center": center, "direction": direction, "diameter": diameter}
                )
    return deduplicate_axes(attachment_points)


def cadquery_to_open3d_mesh(solid):
    exporters.export(solid, TEMP_STL)
    mesh = trimesh.load(TEMP_STL)
    o3d_mesh = o3d.geometry.TriangleMesh()
    o3d_mesh.vertices = o3d.utility.Vector3dVector(mesh.vertices)
    o3d_mesh.triangles = o3d.utility.Vector3iVector(mesh.faces)
    o3d_mesh.compute_vertex_normals()
    return o3d_mesh, mesh


for file in os.listdir(MODEL_DIR):
    if file.lower().endswith(".step") or file.lower().endswith(".stp"):
        part_id = os.path.splitext(file)[0]
        step_path = os.path.join(MODEL_DIR, file)
        print(f"🔧 Processing: {file}")

        shape = cq.importers.importStep(step_path)
        solid = shape.val()

        # Attachment points
        attachment_points = detect_attachment_points(solid)

        # Convert to mesh and visualize
        o3d_mesh, mesh = cadquery_to_open3d_mesh(solid)

        # Bounding box metadata
        bounding_box = mesh.bounding_box.bounds
        size = mesh.bounding_box.extents
        center = mesh.bounding_box.centroid

        # Visualize
        spheres = []
        for pt in attachment_points:
            sphere = o3d.geometry.TriangleMesh.create_sphere(radius=1)
            sphere.translate(pt["center"])
            sphere.paint_uniform_color([1, 0, 0])
            spheres.append(sphere)
        o3d.visualization.draw_geometries([o3d_mesh] + spheres)

        # Save metadata
        metadata = {
            "part_id": part_id,
            "bounding_box": bounding_box.tolist(),
            "bounding_box_size": size.tolist(),
            "bounding_box_center": center.tolist(),
            "attachment_points": attachment_points,
        }
        with open(os.path.join(JSON_DIR, f"{part_id}.json"), "w") as f:
            json.dump(metadata, f, indent=2)

        # Save GLB
        mesh.export(os.path.join(GLB_DIR, f"{part_id}.glb"))

print("✅ Done.")
