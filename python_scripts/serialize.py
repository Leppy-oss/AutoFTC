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

MODELS_DIR = "./models"
GBL_DIR = "./gbl"
SERIALIZED_DIR = "./serialized"

os.makedirs(GBL_DIR, exist_ok=True)
os.makedirs(SERIALIZED_DIR, exist_ok=True)


def get_bounding_box(shape):
    bbox = Bnd_Box()
    brepbndlib.Add(shape, bbox)
    xmin, ymin, zmin, xmax, ymax, zmax = [round(v, 2) for v in bbox.Get()]
    center = [(xmin + xmax) / 2, (ymin + ymax) / 2, (zmin + zmax) / 2]
    size = [xmax - xmin, ymax - ymin, zmax - zmin]
    return {
        "size": size,
        "center": center,
    }

"""
def find_attachment_points(shape):
    explorer = TopExp_Explorer(shape, TopAbs_FACE)
    attachment_points = []
    seen = set()

    while explorer.More():
        face = topods.Face(explorer.Current())
        surf = BRepAdaptor_Surface(face, True)
        surf_type = surf.GetType()

        if surf_type == GeomAbs_Cylinder:
            cylinder = surf.Cylinder()
            radius = cylinder.Radius()
            axis = cylinder.Axis()
            location = axis.Location()
            direction = axis.Direction()

            if radius * 2 >= 3.5:  # Diameter filter
                key = (
                    round(location.X(), 3),
                    round(location.Y(), 3),
                    round(location.Z(), 3),
                    round(direction.X(), 3),
                    round(direction.Y(), 3),
                    round(direction.Z(), 3),
                )
                if key not in seen:
                    seen.add(key)
                    attachment_points.append(
                        {
                            "center": [location.X(), location.Y(), location.Z()],
                            "direction": [direction.X(), direction.Y(), direction.Z()],
                            "radius": radius,
                        }
                    )
        explorer.Next()

    return attachment_points

def get_primary_axis(x, y, z):
    axis_labels = ["X", "Y", "Z"]
    components = [abs(x), abs(y), abs(z)]
    return axis_labels[components.index(max(components))]


def get_face_normal_and_uv_samples(face, samples=3):
    surf_adapt = BRepAdaptor_Surface(face, True)
    u_min, u_max = surf_adapt.FirstUParameter(), surf_adapt.LastUParameter()
    v_min, v_max = surf_adapt.FirstVParameter(), surf_adapt.LastVParameter()

    geom_surface = surf_adapt.Surface().Surface()
    normals = []
    points = []

    for i in range(samples):
        for j in range(samples):
            u = u_min + (u_max - u_min) * (i + 0.5) / samples
            v = v_min + (v_max - v_min) * (j + 0.5) / samples
            props = GeomLProp_SLProps(geom_surface, u, v, 1, 1e-6)

            if props.IsNormalDefined():
                norm = props.Normal()
                pt = props.Value()
                normals.append(norm)
                points.append(pt)

    return list(zip(points, normals))


def is_exterior_face(face, solid_shape, offset_dist=0.5):
    # Get surface properties to find center point
    prop = GProp_GProps()
    brepgprop.SurfaceProperties(face, prop)
    center = prop.CentreOfMass()
    surf_adapt = BRepAdaptor_Surface(face)

    # Attempt to get normal from face center
    try:
        umin, umax, vmin, vmax = (
            surf_adapt.FirstUParameter(),
            surf_adapt.LastUParameter(),
            surf_adapt.FirstVParameter(),
            surf_adapt.LastVParameter(),
        )
        u = (umin + umax) / 2
        v = (vmin + vmax) / 2
        normal = surf_adapt.Normal(u, v)
    except Exception:
        return False  # whoops

    # offset point
    offset_vec = gp_Vec(normal) * offset_dist
    offset_pt = center.Translated(offset_vec)

    # check if outside solid
    classifier = BRepClass3d_SolidClassifier(solid_shape, offset_pt, 1e-6)
    return classifier.State() == TopAbs_OUT


def find_mating_faces(shape):
    explorer = TopExp_Explorer(shape, TopAbs_FACE)
    mating_faces = []

    while explorer.More():
        face = topods.Face(explorer.Current())
        surf = BRepAdaptor_Surface(face, True)
        surf_type = surf.GetType()

        props = GProp_GProps()
        brepgprop.SurfaceProperties(face, props)
        center = props.CentreOfMass()

        # reject interior faces
        bbox = Bnd_Box()
        brepbndlib.Add(face, bbox)
        xmin, ymin, zmin, xmax, ymax, zmax = bbox.Get()
        if bbox.IsVoid():
            explorer.Next()
            continue

        width, height, depth, area = xmax - xmin, ymax - ymin, zmax - zmin, props.Mass()

        if surf_type == GeomAbs_Plane:
            # only accept planar faces >= Xmm in both dimensions
            if sum(1 for dim in (width, height, depth) if dim > 5.0) >= 2 and area > 200:
                print(f"width, height, depth, area = {width}, {height}, {depth}, {area}")
                print(f"is exterior face: {is_exterior_face(face, shape)}")
                if is_exterior_face(face, shape):
                    normal = surf.Plane().Axis().Direction()
                    mating_faces.append({
                        "face": face,
                        "center": [center.X(), center.Y(), center.Z()],
                        "axis": get_primary_axis(normal.X(), normal.Y(), normal.Z()),
                    })

        explorer.Next()

    return mating_faces
"""

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

    bbox_info = get_bounding_box(shape)
    # attachments = find_attachment_points(shape)
    # mating_faces = find_mating_faces(shape)

    # Compute center points of mating faces
    """
    mating_data = []
    for face in mating_faces:
        mating_data.append({
            "center": face["center"],
            "axis": face["axis"]
        })
    """

    data = {
        "pid": part_id,
        "bs": bbox_info["size"],
        "bc": bbox_info["center"],
        # "attachment_points": attachments,
        # "mating_faces": mating_data,
    }

    with open(os.path.join(SERIALIZED_DIR, part_id + ".json"), "w") as f:
        json.dump(data, f, indent=4)

    display, start_display, _add_menu, _add_function_to_menu = init_display("wx")
    display.DisplayShape(shape, update=True)

    # display attachment point spheres
    """
    for pt in attachments:
        p = gp_Pnt(*pt["center"])
        s = BRepPrimAPI_MakeSphere(p, pt["radius"] * 0.5).Shape()
        display.DisplayShape(s, color="RED")

    from OCC.Core.Quantity import Quantity_Color, Quantity_TOC_RGB

    colors = [
        (1.0, 0.0, 0.0),  # red
        (0.0, 1.0, 0.0),  # green
        (0.0, 0.0, 1.0),  # blue
        (1.0, 1.0, 0.0),  # yellow
        (1.0, 0.0, 1.0),  # magenta
        (0.0, 1.0, 1.0),  # cyan
    ]

    for i, entry in enumerate(mating_faces):
        face_shape = entry["face"]
        ais_shape = AIS_Shape(face_shape)
        color = colors[i % len(colors)]
        ais_shape.SetColor(Quantity_Color(*color, Quantity_TOC_RGB))
        display.Context.Display(ais_shape, True)
    """
    display.FitAll()
    print("Press any key in viewer window to continue...")

    def on_key(event=None):
        print("Key pressed, closing viewer.")
        display.EraseAll()
        wx.GetApp().ExitMainLoop()

    display.register_select_callback(lambda *args, **kwargs: on_key())

    """
    def on_key(*args, **kwargs):
        print("Key pressed, closing viewer.")
        wx.GetApp().ExitMainLoop()

    wx.GetApp().GetTopWindow().Bind(wx.EVT_KEY_DOWN, on_key)
    """
    start_display()

    glb_path = os.path.join(GBL_DIR, part_id + ".gltf")
    write_gltf_file(shape, glb_path)
    print(f"Saved GLTF: {glb_path}\n")


if __name__ == "__main__":
    step_files = glob.glob(os.path.join(MODELS_DIR, "*.step")) + glob.glob(
        os.path.join(MODELS_DIR, "*.STEP")
    )

    for filepath in step_files:
        process_step_file(filepath)
