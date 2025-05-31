from OCC.Display.SimpleGui import init_display
from OCC.Core.BRepPrimAPI import BRepPrimAPI_MakeSphere
from OCC.Core.gp import gp_Pnt

display, start_display, add_menu, add_function_to_menu = init_display("wx")

shape = BRepPrimAPI_MakeSphere(gp_Pnt(0, 0, 0), 20).Shape()
display.DisplayShape(shape, update=True)
display.FitAll()

start_display()
