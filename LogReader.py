import json
import os
import fnmatch
import logging
import threading
import time

import dateutil.parser
import tailer

from RouteData import UNKNOWN


class LogReader:
    def __init__(self, route_data, folder_location=None):
        self.log = logging.getLogger(__name__)
        self.route_data = route_data
        self.folder_location = folder_location
        if self.folder_location is None:
            self.default_location()
        self.running = False
        self.log_thread = None

    def default_location(self):
        self.folder_location = os.environ['USERPROFILE'] + '\\Saved Games\\Frontier Developments\\Elite Dangerous'
        self.log.debug("USERPROFILE path: " + os.environ['USERPROFILE'])
        self.log.debug("Full folder path: " + self.folder_location)

    def run(self):
        if self.log_thread is not None:
            raise Exception("Thread already running!")
        self.running = True
        self.log_thread = threading.Thread(target=self.update_log, daemon=True)
        if not self.log_thread.is_alive():
            self.log_thread.start()

    def stop(self):
        self.running = False
        if self.log_thread is not None:
            self.log_thread.join()
            self.log_thread = None

    def update_log(self):
        self.route_data.oldSystem = self.route_data.currentSystem
        self.initialize_current_state()
        while self.running:
            directory = fnmatch.filter(os.listdir(self.folder_location), "Journal.*.log")
            directory.reverse()
            self.log.debug("Directory content: " + str(directory))
            target_log_file = self.folder_location + "\\" + directory[0]
            if self.route_data.checked != target_log_file:
                self.log.debug("Checking log: " + target_log_file)
                self.follow_log(target_log_file)
            else:
                self.log.debug("Elite not running, sleeping a bit")
                time.sleep(10)

        self.log.warning("Got stop signal, terminating CMDR Log following!")

    def initialize_current_state(self):
        initialized = False

        directory = fnmatch.filter(os.listdir(self.folder_location), "Journal.*.log")
        while not initialized:
            filename = directory.pop()
            with open(self.folder_location + "\\" + filename) as file_handle:
                all_lines = file_handle.readlines()
                all_lines.reverse()
            for line in all_lines:
                self.process_line(line, overwrite=False)
                if self.route_data.initialized():
                    initialized = True
                    break

    def follow_log(self, filename):
        self.route_data.activeFile = filename
        with open(filename) as file_handle:
            if self.route_data.checked != self.route_data.activeFile:
                for line in tailer.follow(file_handle):
                    self.process_line(line)
                    if self.route_data.checked == self.route_data.activeFile:
                        break
                    if not self.running:
                        break

    def process_line(self, line, overwrite=True):
        data = json.loads(line)
        if data["event"] == "Shutdown":
            if overwrite:
                # we are at the end of the file, Elite was shutdown
                self.route_data.checked = self.route_data.activeFile
                self.log.info("Elite Dangerous shutdown detected. Waiting for a newer log file.")
                # stop following the log and wait for a newer one
        if data["event"] == "CarrierJump" or data["event"] == "FSDJump" or data["event"] == "Location":
            if self.route_data.currentSystem == UNKNOWN or overwrite:
                system = data["StarSystem"]
                self.log.info("Found current star system: " + system)
                self.route_data.currentSystem = system
        if data["event"] == "CarrierJumpRequest":
            if not overwrite and self.route_data.currentSystem is not UNKNOWN:
                return
            if self.route_data.lastJumpRequest is None or overwrite:
                t = data["timestamp"]
                self.log.debug("CarrierJumpRequest: extracted " + t)
                t = dateutil.parser.parse(t)
                self.log.info("CarrierJumpRequest: found timestamp " + str(t))
                self.route_data.lastJumpRequest = t.timestamp()
                self.route_data.destinationSystem = data["SystemName"]
        if data["event"] == "Cargo" and data["Vessel"] == "Ship":
            if self.route_data.shipInventory is None or overwrite:
                cargo = data["Count"]
                self.log.info('Ship Inventory: ' + str(cargo))
                self.route_data.shipInventory = cargo
        if data["event"] == "CarrierStats":
            if self.route_data.carrierFuel is None or overwrite:
                fuel = data["FuelLevel"]
                self.route_data.carrierFuel = fuel
                self.log.info('Carrier fuel: ' + str(fuel))
            if self.route_data.carrierInventory is None or overwrite:
                cargo = data["SpaceUsage"]["Cargo"]
                self.log.info('Carrier cargo: ' + str(cargo))
                self.route_data.carrierInventory = cargo
        if data["event"] == "CarrierDepositFuel":
            if self.route_data.carrierFuel is None or overwrite:
                fuel = data["Total"]
                self.route_data.carrierFuel = fuel
                self.log.info('Carrier fuel: ' + str(fuel))
        if data["event"] == "CarrierJumpCancelled":
            self.log.info('Carrier jump cancelled!')
            self.route_data.destinationSystem = None
            self.route_data.lastJumpRequest = None


if __name__ == '__main__':
    from RouteData import RouteData

    reader = LogReader(route_data=RouteData())
    reader.update_log()
