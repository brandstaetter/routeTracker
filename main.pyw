from UI import *
from logReader import *
try:
    reader=logReader()
    ui=userInterface(reader=reader)
    ui.mainLoop()
except Exception as e:
    with open('routeTrackerErrorLog.txt','r') as f:
        f.write(e)
