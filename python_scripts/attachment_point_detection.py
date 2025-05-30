import cadquery as cq
from cadquery import exporters
import json
from OCP.GeomAbs import GeomAbs_Circle

# === Configuration ===
STEP_FILE = "1101_Series_U-Beam_17_Hole_136mm_Length.STEP"
OUTPUT_STEP_FILE = "annotated_part.STEP"
METADATA_FILE = "attachment_points.json"
MIN_DIAMETER = 1.0  # mm
MAX_DIAMETER = 10.0  # mm


# === Load STEP File ===
shape = cq.importers.importStep(STEP_FILE)


# === Detect Attachment Points ===
def find_attachment_points(shape, min_diameter, max_diameter):
    attachment_points = []

    for solid in shape.vals():
        for face in solid.Faces():
            for edge in face.Edges():
                curve = edge._geomAdaptor()
                if curve.GetType() == GeomAbs_Circle:
                    radius = curve.Circle().Radius()
                    diameter = 2 * radius
                    if min_diameter <= diameter <= max_diameter:
                        center = face.Center().toTuple()
                        normal = face.normalAt().toTuple()
                        attachment_points.append(
                            {"center": center, "normal": normal, "diameter": diameter}
                        )

    return attachment_points


# === Get and Save Metadata ===
attachment_points = find_attachment_points(shape, MIN_DIAMETER, MAX_DIAMETER)

with open(METADATA_FILE, "w") as f:
    json.dump({"attachment_points": attachment_points}, f, indent=4)


# === Visualize: Add Spheres to Attachment Points ===
annotated = shape
for ap in attachment_points:
    sphere = cq.Workplane("XY").transformed(offset=cq.Vector(*ap["center"])).sphere(1.5)
    annotated = annotated.union(sphere)

exporters.export(annotated, OUTPUT_STEP_FILE)

print(
    f"✅ Success!\n→ JSON metadata: {METADATA_FILE}\n→ Annotated STEP file: {OUTPUT_STEP_FILE}"
)
