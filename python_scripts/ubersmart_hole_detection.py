import wx
import os
import json
import glob
import uuid
import time

from OCC.Core.STEPControl import STEPControl_Reader
from OCC.Core.BRepBndLib import brepbndlib_Add
from OCC.Core.Bnd import Bnd_Box
from OCC.Core.BRep import BRep_Tool
from OCC.Core.BRepPrimAPI import BRepPrimAPI_MakeSphere
from OCC.Core.TopExp import TopExp_Explorer
from OCC.Core.TopAbs import TopAbs_FACE
from OCC.Core import TopoDS
from OCC.Core.GProp import GProp_GProps
from OCC.Core.BRepGProp import brepgprop_SurfaceProperties
from OCC.Display.SimpleGui import init_display
from OCC.Core.BRepBuilderAPI import BRepBuilderAPI_Transform
from OCC.Core.gp import gp_Circ, gp_Pnt, gp_Trsf
from OCC.Core.BRepAdaptor import BRepAdaptor_Surface
from OCC.Core.GeomAbs import GeomAbs_Circle
from OCC.Core.Geom import Geom_Circle
from OCC.Core.IFSelect import IFSelect_RetDone
from OCC.Core.StlAPI import StlAPI_Writer
from OCC.Extend.DataExchange import write_gltf_file
from OCC.Core.GeomAdaptor import GeomAdaptor_Surface

MODELS_DIR = "./models"
GBL_DIR = "./gbl"
SERIALIZED_DIR = "./serialized_models"

os.makedirs(GBL_DIR, exist_ok=True)
os.makedirs(SERIALIZED_DIR, exist_ok=True)


def get_bounding_box(shape):
    bbox = Bnd_Box()
    brepbndlib_Add(shape, bbox)
    xmin, ymin, zmin, xmax, ymax, zmax = bbox.Get()
    center = [(xmin + xmax) / 2, (ymin + ymax) / 2, (zmin + zmax) / 2]
    size = [xmax - xmin, ymax - ymin, zmax - zmin]
    return {
        "bbox": [[xmin, ymin, zmin], [xmax, ymax, zmax]],
        "size": size,
        "center": center,
    }


from OCC.Core.BRepAdaptor import BRepAdaptor_Surface
from OCC.Core.GeomAbs import GeomAbs_Cylinder
from OCC.Core.gp import gp_Pnt
from OCC.Core.TopoDS import topods
from OCC.Core.TopExp import TopExp_Explorer
from OCC.Core.TopAbs import TopAbs_FACE


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
    attachments = find_attachment_points(shape)

    data = {
        "part_id": part_id,
        "bounding_box": bbox_info["bbox"],
        "bounding_box_size": bbox_info["size"],
        "bounding_box_center": bbox_info["center"],
        "attachment_points": attachments,
    }

    with open(os.path.join(SERIALIZED_DIR, part_id + ".json"), "w") as f:
        json.dump(data, f, indent=4)

    # Display model and attachment points
    display, start_display, add_menu, add_function_to_menu = init_display("wx")
    display.DisplayShape(shape, update=True)
    for pt in attachments:
        p = gp_Pnt(*pt["center"])
        s = BRepPrimAPI_MakeSphere(p, pt["radius"] * 0.5).Shape()
        display.DisplayShape(s, color="RED")

    display.FitAll()
    print("Press any key in viewer window to continue...")

    # === Add key handler to quit on any key press ===
    def on_key(*args, **kwargs):
        print("on key trig")
        print("Key pressed, closing viewer.")
        wx.GetApp().ExitMainLoop()

    # Bind the event (wx backend automatically passes key press events)
    
    wx.GetApp().GetTopWindow().Bind(wx.EVT_KEY_DOWN, on_key)

    start_display()

    # Save GLB
    glb_path = os.path.join(GBL_DIR, part_id + ".gltf")  # .gltf/.glb export
    write_gltf_file(shape, glb_path)
    print(f"Saved GLTF: {glb_path}\n")


if __name__ == "__main__":
    step_files = glob.glob(os.path.join(MODELS_DIR, "*.step")) + glob.glob(
        os.path.join(MODELS_DIR, "*.STEP")
    )

    for filepath in step_files:
        process_step_file(filepath)
