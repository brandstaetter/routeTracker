from dataclasses import dataclass

UNKNOWN = 'unknown'


@dataclass(frozen=False)
class RouteData:
    # information from the log
    checked = None
    activeFile = None
    currentSystem = UNKNOWN
    destinationSystem = UNKNOWN
    carrierFuel = None
    carrierInventory = None
    shipInventory = None
    carrierName = UNKNOWN
    oldSystem = UNKNOWN
    lastJumpRequest = None
    # waypoints from the route:
    waypoints = []
    waypointSystemNames = []
    position = 0

    def clear(self):
        self.checked = None
        self.activeFile = None
        self.destinationSystem = UNKNOWN
        self.carrierFuel = None
        self.carrierInventory = None
        self.shipInventory = None
        self.carrierName = UNKNOWN
        self.oldSystem = UNKNOWN
        self.lastJumpRequest = None

    def initialized(self) -> bool:
        return self.carrierFuel is not None \
               and self.carrierInventory is not None \
               and self.currentSystem is not None \
               and self.shipInventory is not None
