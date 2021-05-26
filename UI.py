import csv
import threading

import tkinter as tk
import ctypes
import logging
import time
import math
import pickle
import winsound
from tkinter.filedialog import askopenfilename, askdirectory
from tkinter import messagebox
import pyperclip
import webbrowser

from LogReader import LogReader
from RouteData import RouteData, UNKNOWN
from RouteReader import RouteReader

ORANGE = 'orange'
BLUE = 'blue'
RED = 'red'
BLACK = 'black'
GREEN = 'green'
GREEN_BRIGHT = '#00ff00'

FONT_15 = "Ebrima 15 bold"
FONT_13 = "Ebrima 13 bold"
FONT_08 = "Ebrima 8 bold"

WP_SYSTEM_NAME = "System Name"
WP_FUEL_USED = "Fuel Used"

START_Y = 290

BOX_HEIGHT = 20
VERTICAL_SPACING = 25
SCROLL_LENGTH = 10

TRACKER_DATA_TXT = "trackerData.txt"


class POINT(ctypes.Structure):
    _fields_ = [("x", ctypes.c_ulong), ("y", ctypes.c_ulong)]


def pickle_data(data_template):
    try:
        with open(TRACKER_DATA_TXT, "rb") as f:
            return pickle.load(f)
    except FileNotFoundError:
        with open(TRACKER_DATA_TXT, "wb") as f:
            pickle.dump(data_template, f)
            return data_template


def mouse_position():
    pt = POINT()
    ctypes.windll.user32.GetCursorPos(ctypes.byref(pt))
    return int(pt.x), int(pt.y)


class UserInterface:

    def __init__(self):
        self.log = logging.getLogger(__name__)
        user32 = ctypes.windll.user32
        width, height = user32.GetSystemMetrics(0), user32.GetSystemMetrics(1)
        data_template = {'window position': [width / 2 - 250, height / 4], 'route positions': {}, 'showType': 'show',
                         'topmost': 1, 'alarm': True, 'logLocation': '', 'shipCargo': 0, 'carrierCargo': 0,
                         'more': False}
        self.exiting = False
        self.maxCountdown = 60 * 21

        self.logCheck = 30
        self.route_data = RouteData()
        self.logReader = LogReader(self.route_data)
        self.route_reader = RouteReader(self.route_data)

        self.canvas = None
        self.root = None
        self.window = None
        self.settingsWindow = None
        self.hidden = False
        self.scroll = 0
        self.scrollHeight = VERTICAL_SPACING * (SCROLL_LENGTH - 1) + BOX_HEIGHT
        self.dragOffset = [0, 0]
        self.barCentre = None
        self.scrolling = False
        self.startDrag = None
        self.alarmButton = None
        self.logLocationLabel = None
        self.carrierGoodsEntry = None
        self.shipGoodsEntry = None

        self.countdown = self.maxCountdown
        self.countdownStart = time.time()
        self.logStart = 0

        self.system = None
        self.nextSystem = UNKNOWN
        self.currentFile = None

        self.position = 0

        self.dragging = False
        self.draggingPos = [width / 2 - 250, height / 4]

        self.scrollTop = [0, 0]
        self.scrollBottom = [0, 0]

        self.data = pickle_data(data_template)
        self.add_missing_data_from_template(data_template)

        if self.data['logLocation'] != '':
            self.logReader.folder_location = self.data['logLocation']
        self.create_window()

    def add_missing_data_from_template(self, data_template):
        added = False
        data_keys = list(self.data.keys())
        for i in list(data_template.keys()):
            if i not in data_keys:
                self.data[i] = data_template[i]
                added = True
        if added:
            self.save_data()

    def main_loop(self):
        time_loop = time.time()

        if "current file" in list(self.data.keys()):
            self.currentFile = self.data["current file"]
            self.open_file(dialogue=False)

        self.logReader.run()

        while True:
            time.sleep(0.01)
            try:
                pyperclip.paste()
                if self.exiting:
                    self.save_data()
                    self.destroy_windows()

                    break
                current_time = time.time()
                if current_time - self.logStart > self.logCheck and self.route_data.waypoints is not None:
                    self.logStart = current_time

                    self.log.debug('Old system: %s, current system: %s, destination: %s',
                                   self.route_data.oldSystem,
                                   self.route_data.currentSystem,
                                   self.route_data.destinationSystem)
                    if self.route_data.oldSystem != self.route_data.currentSystem:
                        self.log.info("Jumped to " + self.route_data.currentSystem)
                        self.route_data.oldSystem = self.route_data.currentSystem
                        self.nextSystem = self.route_data.destinationSystem
                        if self.nextSystem is None:
                            self.nextSystem = UNKNOWN
                        for i in range(self.position, len(self.route_data.waypoints)):
                            self.log.debug('Processing ' + self.route_data.waypoints[i][WP_SYSTEM_NAME])
                            if self.route_data.waypoints[i][WP_SYSTEM_NAME] == self.route_data.currentSystem:

                                if self.route_data.waypoints[i + 1][WP_SYSTEM_NAME] == \
                                        self.route_data.waypoints[i][WP_SYSTEM_NAME]:
                                    self.position = i + 1
                                    self.log.debug('double entry in csv list')
                                else:
                                    self.position = i
                                self.nextSystem = self.route_data.waypoints[self.position+1][WP_SYSTEM_NAME]
                                pyperclip.copy(self.nextSystem)
                                self.log.info('copied ' + self.nextSystem + ' to clipboard')
                                self.data['route positions'][self.currentFile] = self.position
                                self.save_data()
                                self.clear()
                                break
                import _tkinter
                try:
                    self.root.update()

                    x, y = mouse_position()
                    if self.dragging:

                        self.data['window position'] = [x - self.dragOffset[0], y - self.dragOffset[1]]
                        self.clear()
                    elif self.scrolling and SCROLL_LENGTH < len(self.route_data.waypoints):
                        proportion = (y - self.barCentre - self.scrollTop[1]) / self.scrollHeight
                        self.scroll = round(proportion * len(self.route_data.waypoints) - self.position)
                        if self.scroll + self.position < 0:
                            self.scroll = -self.position
                        if self.scroll + self.position >= len(self.route_data.waypoints) - SCROLL_LENGTH:
                            self.scroll = len(self.route_data.waypoints) - self.position - SCROLL_LENGTH
                        self.clear()
                    elif current_time - time_loop > 1:
                        self.clear()
                        time_loop = current_time

                    self.settingsWindow.update()
                except AttributeError:
                    # window does not exist yet
                    pass
                except _tkinter.TclError:
                    # window has already been destroyed
                    pass
                except Exception:
                    self.log.exception("Error updating settingsWindow")
                    pass
            except pyperclip.PyperclipWindowsException:
                self.log.debug("PyperclipWindowsException")
                time.sleep(2)

    def destroy_windows(self):
        if self.window is not None:
            self.window.destroy()
        if self.root is not None:
            self.root.destroy()
        if self.settingsWindow is not None:
            self.settingsWindow.destroy()

    def open_file(self, dialogue=True):
        self.scroll = 0
        if dialogue:
            self.currentFile = askopenfilename()
        if self.currentFile != '':
            self.data["current file"] = self.currentFile
            self.log.debug('Current route file: ' + self.currentFile)
            self.log.debug('Data: ' + str(self.data))
            if self.currentFile in list(self.data['route positions'].keys()):
                self.position = self.data['route positions'][self.currentFile]
            else:
                self.position = 0
                self.data['route positions'][self.currentFile] = self.position
            self.save_data()
            try:
                self.route_reader.read_route_file(self.currentFile)
            except FileNotFoundError as e:
                self.log.exception("Import Error")
                messagebox.showerror("Import Error", e)
            self.clear()

    def save_data(self):
        self.log.info('Saving routeTracker data')
        with open(TRACKER_DATA_TXT, "wb") as f:
            pickle.dump(self.data, f)

    # overlay functions

    def clear(self):

        # all to change with new UI

        try:
            self.canvas.destroy()
        except Exception:
            self.log.debug("Exception during canvas destroy")
            pass

        clip = pyperclip.paste()

        x, y = self.data['window position'][0], self.data['window position'][1]

        self.canvas = tk.Canvas(self.window, bg="pink", bd=0, highlightthickness=0, relief='ridge')
        self.canvas.pack(fill="both", expand=True)

        self.canvas.create_rectangle(x, y, x + 520, y + 30, fill=BLACK)
        if self.route_data.currentSystem == clip:
            fill = GREEN
        elif self.route_data.currentSystem not in self.route_data.waypointSystemNames:
            fill = RED
            if len(self.route_data.waypoints) > self.position:
                self.nextSystem = self.route_data.waypoints[self.position][WP_SYSTEM_NAME]
        else:
            fill = ORANGE
        self.canvas.create_text(x + 5, y + 5, text=self.route_data.currentSystem, font=FONT_13,
                                fill=fill, anchor='nw')
        self.canvas.create_rectangle(x + 150, y, x + 500, y + 30, fill=BLACK)

        self.canvas.create_text(x + 158, y + 5, text='>>  ', font=FONT_13, fill=ORANGE, anchor='nw')

        if self.nextSystem == clip:
            self.canvas.create_text(x + 190, y + 5, text=self.nextSystem, font=FONT_13, fill=GREEN,
                                    anchor='nw')
        else:
            self.canvas.create_text(x + 190, y + 5, text=self.nextSystem, font=FONT_13, fill=ORANGE,
                                    anchor='nw')

        self.canvas.create_rectangle(x + 340, y, x + 500, y + 30, fill=BLACK)

        if self.route_data.lastJumpRequest is not None:
            time_since = time.time() - self.route_data.lastJumpRequest
            time_since = self.maxCountdown - time_since
        else:
            time_since = 0

        if time_since > 0:
            if time_since < 10 and self.data['alarm']:
                winsound.Beep(3000, 100)
            minutes = str(round(time_since // 60))
            seconds = str(math.floor(time_since % 60))
            if len(minutes) == 1:
                minutes = '0' + minutes
            if len(seconds) == 1:
                seconds = '0' + seconds
            text = minutes + ':' + seconds
        else:
            text = 'Ready'
        text = '| ' + text + ' |'

        self.canvas.create_text(x + 350, y + 5, text=text, font=FONT_13, fill=ORANGE, anchor='nw')

        self.canvas.create_text(x + 420, y + 5, text='☰', font=FONT_13, fill=ORANGE, anchor='nw')

        self.canvas.create_text(x + 440, y + 5, text='📁', font=FONT_13, fill=ORANGE, anchor='nw')

        self.canvas.create_text(x + 463, y + 5, text='⚙', font=FONT_13, fill=ORANGE, anchor='nw')
        if self.data['topmost'] == 1:
            self.canvas.create_text(x + 485, y + 5, text='⮝', font=FONT_13, fill=ORANGE, anchor='nw')

        else:
            self.canvas.create_text(x + 485, y + 5, text='⮟', font=FONT_13, fill=ORANGE, anchor='nw')

        self.canvas.create_text(x + 500, y + 5, text='✘', font=FONT_13, fill=ORANGE, anchor='nw')

        self.canvas.create_line(x, y, x + 520, y, fill=ORANGE)
        self.canvas.create_line(x, y + 30, x + 520, y + 30, fill=ORANGE)
        if self.data['more']:
            self.create_dashboard()

    def create_dashboard(self):

        x, y = self.data['window position'][0], self.data['window position'][1]
        try:
            self.canvas.create_rectangle(x, y + 35, x + 520, y + 600, fill=BLACK, outline=ORANGE)

            if len(self.route_data.waypoints) == 0:
                return
            if not self.route_data.initialized():
                return

            self.draw_progress(x, y)
            self.draw_cargo_fuel_panel(x, y)
            self.draw_waypoint_list(x, y)

        except IndexError:
            self.log.exception("Unexpected index error")
            self.canvas.create_rectangle(x, y + 35, x + 520, y + 600, fill=BLACK, outline=ORANGE)
        except Exception:
            self.log.exception("Error creating dashboard")

            self.canvas.create_rectangle(x, y + 35, x + 520, y + 600, fill=BLACK, outline=ORANGE)

    def draw_progress(self, x, y):
        # panel background
        self.canvas.create_rectangle(x + 10, y + 40, x + 510, y + 150, fill='#111111', outline='#333333')

        above = True
        increment = 1
        displayed_waypoints = len(self.route_data.waypoints)
        max_displayed_waypoints = 5
        while displayed_waypoints % max_displayed_waypoints != 0 and max_displayed_waypoints >= 2:
            max_displayed_waypoints -= 1
        if displayed_waypoints > max_displayed_waypoints:
            increment = math.ceil(displayed_waypoints / max_displayed_waypoints)
        for i in range(0, displayed_waypoints - 1, increment):
            anchor = 'w'
            if i >= displayed_waypoints / 5:
                anchor = 'center'
            if i > displayed_waypoints * 4 / 5:
                anchor = 'e'
            hor_pos = i / displayed_waypoints * 480 + 20
            if above:

                self.canvas.create_rectangle(x + hor_pos - 8, y + 45, x + 500, y + 80, fill='#111111',
                                             outline='#111111')
                self.canvas.create_line(x + hor_pos, y + 70, x + hor_pos, y + 80, fill=ORANGE)
                self.canvas.create_text(x + hor_pos, y + 60, text=self.route_data.waypoints[i][WP_SYSTEM_NAME] + "   ",
                                        font=FONT_08, fill=ORANGE, anchor=anchor)
            else:

                self.canvas.create_rectangle(x + hor_pos - 8, y + 80, x + 500, y + 120, fill='#111111',
                                             outline='#111111')
                self.canvas.create_line(x + hor_pos, y + 80, x + hor_pos, y + 90, fill=ORANGE)
                self.canvas.create_text(x + hor_pos, y + 95, text=self.route_data.waypoints[i][WP_SYSTEM_NAME] + "   ",
                                        font=FONT_08, fill=ORANGE, anchor=anchor)

            above = not above
        hor_pos = 500
        if above:
            self.canvas.create_rectangle(x + hor_pos - 10, y + 45, x + 500, y + 80, fill='#111111',
                                         outline='#111111')
            self.canvas.create_line(x + hor_pos, y + 70, x + hor_pos, y + 80, fill=ORANGE)
            self.canvas.create_text(x + hor_pos, y + 60, text="   " + self.route_data.waypoints[-1][WP_SYSTEM_NAME],
                                    font=FONT_08, fill=ORANGE, anchor='e')
        else:
            self.canvas.create_rectangle(x + hor_pos - 10, y + 80, x + 500, y + 120, fill='#111111',
                                         outline='#111111')
            self.canvas.create_line(x + hor_pos, y + 80, x + hor_pos, y + 90, fill=ORANGE)
            self.canvas.create_text(x + hor_pos, y + 95, text="   " + self.route_data.waypoints[-1][WP_SYSTEM_NAME],
                                    font=FONT_08, fill=ORANGE, anchor='e')
        self.canvas.create_line(x + 20, y + 80, x + 500, y + 80, fill=ORANGE, width=2)
        if self.position == 0:
            self.canvas.create_oval(x + 15, y + 75, x + 25, y + 85, fill=ORANGE, outline=ORANGE)
        else:
            self.canvas.create_oval(x + 15, y + 75, x + 25, y + 85, fill=GREEN, outline=GREEN)
        if self.position == displayed_waypoints:
            self.canvas.create_oval(x + 495, y + 75, x + 505, y + 85, fill=GREEN, outline=GREEN)
        else:
            self.canvas.create_oval(x + 495, y + 75, x + 505, y + 85, fill=ORANGE, outline=ORANGE)
        self.canvas.create_text(x + 20, y + 130, text="Jumps   |  Completed: " + str(self.position),
                                font=FONT_13, fill=ORANGE, anchor='w')
        for i in range(displayed_waypoints):
            diff = i - self.position
            if diff >= 0:
                self.canvas.create_text(x + 220, y + 130, text="|  To Waypoint: " + str(diff), font=FONT_13,
                                        fill=ORANGE, anchor='w')
                break
        self.canvas.create_text(x + 380, y + 130,
                                text="|  Left: " + str(displayed_waypoints - self.position - 1),
                                font=FONT_13, fill=ORANGE, anchor='w')
        if displayed_waypoints > 2:
            for i in range(displayed_waypoints):
                hor_pos = i / displayed_waypoints * 480 + 20
                draw_color = ORANGE
                if i <= self.position:
                    draw_color = GREEN
                self.canvas.create_oval(x + hor_pos - 3, y + 77, x + hor_pos + 3, y + 83, fill=draw_color,
                                        outline=draw_color)
        hor_pos = self.position / (len(self.route_data.waypoints)) * 480 + 20
        self.canvas.create_polygon(x + hor_pos - 5, y + 85, x + hor_pos, y + 75, x + hor_pos + 5, y + 85,
                                   fill=GREEN_BRIGHT, outline=GREEN_BRIGHT)

    def draw_cargo_fuel_panel(self, x, y):
        # panel background
        self.canvas.create_rectangle(x + 10, y + 160, x + 510, y + 270, fill='#111111', outline='#333333')

        req_fuel = self.route_data.waypoints[self.position][WP_FUEL_USED]
        req_fuel = int(req_fuel)
        if req_fuel > 0:
            req_fuel += 1000
        else:
            for i in range(self.position, len(self.route_data.waypoints)):
                req_fuel += int(self.route_data.waypoints[i][WP_FUEL_USED])
            req_fuel -= int(self.route_data.waypoints[self.position][WP_FUEL_USED])
        fuel_total = self.draw_fuel_bar(req_fuel, x, y)
        self.draw_fuel_messages(fuel_total, req_fuel, x, y)

    def draw_fuel_bar(self, req_fuel, x, y):
        if not self.route_data.initialized():
            return
        carrier_fuel = self.route_data.carrierFuel
        ship_fuel = self.route_data.shipInventory - self.data['shipCargo']
        carrier_cargo = self.route_data.carrierInventory - self.data['carrierCargo']
        self.canvas.create_text(x + 20, y + 180, text="Tritium | ", font=FONT_13, fill=ORANGE,
                                anchor='w')
        self.canvas.create_text(x + 95, y + 180, text=" Tank: " + str(carrier_fuel), font=FONT_13,
                                fill=GREEN, anchor='w')
        self.canvas.create_text(x + 190, y + 180, text="| Ship: " + str(ship_fuel), font=FONT_13,
                                fill=BLUE, anchor='w')
        self.canvas.create_text(x + 280, y + 180, text="| Cargo: " + str(carrier_cargo), font=FONT_13,
                                fill=ORANGE, anchor='w')
        self.canvas.create_text(x + 260, y + 197,
                                text="Please note you need to open the carrier management page to update this.",
                                font=FONT_08, fill=ORANGE)
        self.canvas.create_text(x + 400, y + 180, text=" | Min: " + str(req_fuel), font=FONT_13, fill=RED,
                                anchor='w')
        fuel_total = carrier_fuel + ship_fuel
        width = max(fuel_total + carrier_cargo, req_fuel) / 480
        self.canvas.create_rectangle(x + 20, y + 210, x + 20 + req_fuel / width, y + 230, fill=RED, outline=RED,
                                     stipple='gray25')
        self.canvas.create_rectangle(x + 20, y + 210, x + 20 + carrier_fuel / width, y + 230, fill=GREEN,
                                     outline=GREEN)
        self.canvas.create_rectangle(x + 20 + carrier_fuel / width, y + 210,
                                     x + 20 + ship_fuel / width + carrier_fuel / width, y + 230, fill=BLUE,
                                     outline=BLUE)
        self.canvas.create_rectangle(x + 20 + ship_fuel / width + carrier_fuel / width, y + 210,
                                     x + 20 + ship_fuel / width + carrier_fuel / width + carrier_cargo / width,
                                     y + 230,
                                     fill=ORANGE, outline=ORANGE)
        self.canvas.create_rectangle(x + 20 + req_fuel / width - 2, y + 210, x + 20 + req_fuel / width, y + 230,
                                     fill=RED, outline=RED)
        return fuel_total

    def draw_fuel_messages(self, fuel_total, req_fuel, x, y):
        diff = fuel_total - req_fuel
        if diff >= 0:
            self.canvas.create_text(x + 260, y + 250, text="You are " + str(diff) + " Tritium in excess",
                                    font=FONT_13, fill=GREEN)
        else:
            self.canvas.create_text(x + 260, y + 250, text="Warning! You are " + str(-diff) + " Tritium short!",
                                    font=FONT_13, fill=RED)

    def draw_waypoint_list(self, x, y):
        # panel background
        self.canvas.create_rectangle(x + 10, y + 280, x + 510, y + 540, fill='#111111', outline='#333333')
        # routeList
        bar_height = min(SCROLL_LENGTH / (len(self.route_data.waypoints)) * self.scrollHeight, self.scrollHeight)
        self.barCentre = bar_height / 2
        bar_position = y + (self.position + self.scroll) / (
            len(self.route_data.waypoints)) * self.scrollHeight + START_Y
        for i in range(SCROLL_LENGTH):
            if self.position + self.scroll + i < len(self.route_data.waypoints):
                if self.route_data.waypoints[self.position + self.scroll + i] == pyperclip.paste():
                    box_fill = GREEN
                    text_fill = BLACK
                elif self.scroll + i == 0:
                    box_fill = ORANGE
                    text_fill = BLACK
                elif self.position + self.scroll + i in self.route_data.waypoints \
                        or self.position + self.scroll + i - 1 in self.route_data.waypoints:
                    box_fill = RED
                    text_fill = BLACK

                else:
                    box_fill = BLACK
                    text_fill = ORANGE

                self.canvas.create_rectangle(x + 15, y + START_Y + VERTICAL_SPACING * i, x + 490,
                                             y + START_Y + VERTICAL_SPACING * i + BOX_HEIGHT, fill=box_fill,
                                             outline=ORANGE)
                self.canvas.create_text(x + 17, y + START_Y + VERTICAL_SPACING * i,
                                        text=self.route_data.waypoints[self.position + self.scroll + i][WP_SYSTEM_NAME],
                                        font=FONT_13, fill=text_fill, anchor='nw')
        self.canvas.create_rectangle(x + 497, y + START_Y, x + 505, y + START_Y + self.scrollHeight, fill=BLACK,
                                     outline=ORANGE)
        self.scrollTop = [x + 497, y + START_Y]
        self.scrollBottom = [x + 505, y + START_Y + VERTICAL_SPACING * (SCROLL_LENGTH - 1) + BOX_HEIGHT]
        self.canvas.create_rectangle(x + 497, bar_position, x + 505, bar_position + bar_height, fill=ORANGE,
                                     outline=ORANGE)
        for i in range(len(self.route_data.waypoints)):
            bar_position = y + i / (len(self.route_data.waypoints)) * self.scrollHeight + START_Y
            self.canvas.create_rectangle(x + 497, bar_position, x + 505, bar_position + 1, fill=RED,
                                         outline=RED)
        bar_position = y + self.position / (len(self.route_data.waypoints)) * self.scrollHeight + START_Y
        self.canvas.create_rectangle(x + 497, bar_position, x + 505, bar_position + 1, fill=ORANGE,
                                     outline=ORANGE)

    def mouse_down(self, values):
        self.startDrag = time.time()
        if self.scrollTop[0] <= values.x <= self.scrollBottom[0] \
                and self.scrollTop[1] <= values.y <= self.scrollBottom[1] \
                and not self.dragging:

            self.scrolling = True
        elif not self.scrolling:

            self.dragging = True

            self.dragOffset = [values.x - self.data['window position'][0], values.y - self.data['window position'][1]]

    def end_drag(self, values):
        self.dragging = False
        self.scrolling = False

        rel_x = values.x - self.data['window position'][0]
        if time.time() - self.startDrag < 0.3 and values.y - self.data['window position'][1] < 30:

            if rel_x < 150:
                pyperclip.copy(self.route_data.currentSystem)
                self.log.info('Copied ' + self.route_data.currentSystem + ' to clipboard')

            elif 190 < rel_x < 340:
                pyperclip.copy(self.nextSystem)
                self.log.info('Copied ' + self.nextSystem + ' to clipboard')

            # more
            elif 420 < rel_x < 440:
                self.data['more'] = not self.data['more']

                pass
            # open route
            elif 440 < rel_x < 463:
                self.open_file()
            # settings
            elif 463 < rel_x < 485:
                self.settings()
                pass

            # minimise
            elif 485 < rel_x < 500:

                self.data['topmost'] = -self.data['topmost'] + 1
                self.create_window()

            # close
            elif 500 < rel_x < 520:
                self.exiting = True

            self.save_data()

        elif time.time() - self.startDrag < 0.3 and 15 < rel_x < 490:
            proportion = (values.y - self.scrollTop[1]) / self.scrollHeight
            clicked_on = proportion * SCROLL_LENGTH
            system_name = self.route_data.waypoints[math.floor(self.position + self.scroll + clicked_on)][
                WP_SYSTEM_NAME]
            pyperclip.copy(system_name)
            self.log.debug("Copied %s", system_name)

        self.clear()

    def wheel(self, values):

        if SCROLL_LENGTH < len(self.route_data.waypoints):
            self.scroll += round(-values.delta / 100)
            if self.scroll + self.position < 0:
                self.scroll = -self.position
            if self.scroll + self.position >= len(self.route_data.waypoints) - SCROLL_LENGTH:
                self.scroll = len(self.route_data.waypoints) - self.position - SCROLL_LENGTH
            self.clear()

    def create_window(self):
        import _tkinter
        try:
            self.root.destroy()
            self.window.destroy()
        except _tkinter.TclError:
            # window has already been destroyed
            pass

        except AttributeError:
            self.log.debug('no root window exists yet')

        self.hidden = False
        user32 = ctypes.windll.user32

        width, height = user32.GetSystemMetrics(0), user32.GetSystemMetrics(1)
        self.root = tk.Tk()
        self.root.title('routeTracker')
        self.root.attributes('-alpha', 0.0)  # For icon
        self.root.iconify()
        if self.data['topmost'] == 1:
            self.window = tk.Toplevel(self.root, highlightthickness=0)
        else:
            self.window = tk.Tk()
        self.window.title('routeTracker')
        self.window.config(bg="pink")
        self.window.geometry(str(width) + "x" + str(height))  # Whatever size

        if self.data['topmost'] == 1:
            self.window.overrideredirect(1)  # Remove border
            self.window.attributes('-topmost', 1)
        else:
            self.window.wm_attributes('-fullscreen', 'true')
            self.root.overrideredirect(1)

        self.window.wm_attributes("-transparentcolor", "pink")
        self.window.bind('<ButtonPress-1>', self.mouse_down)
        self.window.bind('<ButtonRelease-1>', self.end_drag)
        self.window.bind("<MouseWheel>", self.wheel)

        self.clear()

    # settings window
    def alarm(self):
        self.data['alarm'] = not self.data['alarm']
        self.save_data()
        self.alarmButton.config(text='Alarm: ' + str(self.data['alarm']))

    def log_location(self):

        self.data['logLocation'] = askdirectory()
        self.log.debug(self.data['logLocation'])
        if self.data['logLocation'] != '':
            self.logReader.folder_location = self.data['logLocation']
        else:
            self.logReader.default_location()

        self.save_data()
        self.logLocationLabel.config(text=self.logReader.folder_location)

    def cargo_change(self, values):
        can_be_int = False
        value = self.carrierGoodsEntry.get()
        try:
            value = int(value)
            can_be_int = True
        except Exception:
            self.log.exception("Error processing carrier goods")
            pass
        if can_be_int:
            self.data['carrierCargo'] = value

        can_be_int = False
        value = self.shipGoodsEntry.get()
        try:
            value = int(value)
            can_be_int = True
        except Exception:
            self.log.exception("Error processing carrier goods")
            pass
        if can_be_int:
            self.data['shipCargo'] = value

        self.save_data()

    def settings(self):
        try:
            self.settingsWindow.destroy()
        except AttributeError:
            self.log.debug('Settings window does not exist yet')

        self.settingsWindow = tk.Tk()
        self.settingsWindow.title('Settings')
        self.settingsWindow.config(bg=BLACK)

        settings_label = tk.Label(self.settingsWindow, text='Settings\n', font=FONT_15, fg=ORANGE,
                                  bg=BLACK)
        settings_label.grid(row=0, column=0, columnspan=2)

        # log reader file path
        open_browser_button = tk.Button(self.settingsWindow,
                                        text='Log File Location',
                                        font=FONT_13,
                                        fg=ORANGE,
                                        activeforeground=ORANGE,
                                        bg='#222222',
                                        activebackground='#111111',
                                        width=25,
                                        command=self.log_location)
        open_browser_button.grid(row=1, column=0)
        self.logLocationLabel = tk.Label(self.settingsWindow, text=self.logReader.folder_location,
                                         font=FONT_15,
                                         fg=ORANGE, bg=BLACK)
        self.logLocationLabel.grid(row=1, column=1)

        # alarm

        self.alarmButton = tk.Button(self.settingsWindow,
                                     text='Alarm: ' + str(self.data['alarm']),
                                     font=FONT_13,
                                     fg=ORANGE,
                                     activeforeground=ORANGE,
                                     bg='#333333',
                                     activebackground='#222222',
                                     width=25,
                                     command=self.alarm)
        self.alarmButton.grid(row=2, column=0)
        # non tritium goods in carrier
        carrier_goods = tk.Button(self.settingsWindow,
                                  text='Carrier Goods',
                                  font=FONT_13,
                                  fg=ORANGE,
                                  activeforeground=ORANGE,
                                  bg='#222222',
                                  activebackground='#111111',
                                  width=25,
                                  )
        carrier_goods.grid(row=3, column=0)

        self.carrierGoodsEntry = tk.Entry(self.settingsWindow, bg='#222222', fg=ORANGE, bd=0, font=FONT_13)
        self.carrierGoodsEntry.insert(0, str(self.data['carrierCargo']))
        self.carrierGoodsEntry.grid(row=3, column=1)
        # non tritium goods in ship
        ship_goods = tk.Button(self.settingsWindow,
                               text='Ship Goods',
                               font=FONT_13,
                               fg=ORANGE,
                               activeforeground=ORANGE,
                               bg='#333333',
                               activebackground='#222222',
                               width=25,
                               )
        ship_goods.grid(row=4, column=0)

        self.shipGoodsEntry = tk.Entry(self.settingsWindow, bg='#222222', fg=ORANGE, bd=0, font=FONT_13)
        self.shipGoodsEntry.insert(0, str(self.data['shipCargo']))
        self.shipGoodsEntry.grid(row=4, column=1)
        # Thanks

        invite = tk.Button(self.settingsWindow,
                           text="With thanks to the Fleet Carrier Owner's Club",
                           font=FONT_13,
                           fg=ORANGE,
                           activeforeground=ORANGE,
                           bg='#222222',
                           activebackground='#111111',
                           width=50,
                           command=lambda: webbrowser.open('https://discord.gg/tcMPHfh'))
        invite.grid(row=5, column=0, columnspan=2)

        self.settingsWindow.bind("<KeyRelease>", self.cargo_change)


if __name__ == '__main__':
    ui = UserInterface()
    ui.main_loop()
