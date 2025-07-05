import os
from OCC.Core.STEPControl import STEPControl_Reader
from OCC.Core.BRepMesh import BRepMesh_IncrementalMesh
from OCC.Extend.DataExchange import write_gltf_file
import open3d as o3d


def load_step(file_path):
    step_reader = STEPControl_Reader()
    status = step_reader.ReadFile(file_path)
    if status != 1:  # IFSelect_RetDone
        raise Exception(f"Failed to read STEP file: {file_path}")
    step_reader.TransferRoots()
    return step_reader.Shape()


def mesh_shape(shape, deflection=0.1):
    mesh = BRepMesh_IncrementalMesh(shape, deflection)
    mesh.Perform()
    if not mesh.IsDone(): raise Exception("Meshing not completed")
    return shape


def shape_to_glb(shape, output_path):
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    write_gltf_file(shape, output_path, binary=True)
    print(f"Saved GLB file: {output_path}")


def simplify_glb_vertex_clustering(input_glb_path, output_glb_path, voxel_divisor=32):
    mesh = o3d.io.read_triangle_mesh(input_glb_path)

    if mesh.is_empty():
        raise Exception("Failed to load mesh from GLB file with Open3D")

    bbox = mesh.get_max_bound() - mesh.get_min_bound()
    voxel_size = max(bbox) / voxel_divisor
    print(f"Voxel size for clustering: {voxel_size:e}")

    simplified_mesh = mesh.simplify_vertex_clustering(
        voxel_size=voxel_size,
        contraction=o3d.geometry.SimplificationContraction.Average,
    )

    # Post-clean simplified mesh
    simplified_mesh.remove_duplicated_vertices()
    simplified_mesh.remove_duplicated_triangles()
    simplified_mesh.remove_degenerate_triangles()
    simplified_mesh.remove_non_manifold_edges()
    simplified_mesh.compute_vertex_normals()

    print(f"Original vertices: {len(mesh.vertices)}, triangles: {len(mesh.triangles)}")
    print(
        f"Simplified vertices: {len(simplified_mesh.vertices)}, triangles: {len(simplified_mesh.triangles)}"
    )

    print("Is simplified mesh watertight? ", simplified_mesh.is_watertight())

    o3d.io.write_triangle_mesh(output_glb_path, simplified_mesh)
    print(f"Simplified GLB saved: {output_glb_path}")


if __name__ == "__main__":
    step_path = "./models/ClampCollar6ID.STEP"
    glb_original = "./glb/original.glb"
    glb_simplified = "./glb/simplified_vertex_clustering"

    # Load and mesh original shape (fine mesh)
    shape = load_step(step_path)
    mesh_shape(shape, deflection=0.1)
    shape_to_glb(shape, glb_original)

    # Simplify the exported GLB mesh using vertex clustering
    simplify_glb_vertex_clustering(glb_original, f"{glb_simplified}.glb", voxel_divisor=512)
    # for voxel_divisor in range(32, 68, 4):
        # simplify_glb_vertex_clustering(glb_original, f"{glb_simplified}_{voxel_divisor}.glb", voxel_divisor=voxel_divisor)
