import csv
import logging

WP_SYSTEM_NAME = "System Name"


class RouteReader:

    def __init__(self, route_data):
        self.log = logging.getLogger(__name__)
        self.route_data = route_data

    def read_route_file(self, filename):
        with open(filename, 'r') as f:
            current_file_data = csv.DictReader(f)

            self.log.debug('Current file data: ' + str(current_file_data.fieldnames))

            waypoints = []
            system_names = []
            for row in current_file_data:
                waypoints.append(row)
                system_names.append(row[WP_SYSTEM_NAME])
                self.log.debug('Found waypoint: ' + row[WP_SYSTEM_NAME])
        self.log.debug('Route read: ' + str(waypoints))
        self.route_data.waypoints = waypoints
        self.route_data.waypointSystemNames = system_names
