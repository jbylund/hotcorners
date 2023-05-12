"""Hotcorners"""

import argparse
import configparser
import os
import subprocess
import time
import cachetools.func

from Xlib import X, display
from Xlib.ext.xtest import fake_input


def kill_running_instances():
    print("Attempting to kill any running instances...")
    os.system("pkill -9 -f bl-hotcorners")

CONFIG_SECTION = "Hot Corners"

BOTTOM_LEFT = "bottom_left_corner_command"
BOTTOM_RIGHT = "bottom_right_corner_command"
TOP_LEFT = "top_left_corner_command"
TOP_RIGHT = "top_right_corner_command"


@cachetools.func.ttl_cache(maxsize=1, ttl=10)
def get_action_map():
    config = configparser.ConfigParser()
    cfgdir = os.getenv("HOME") + "/.config/bl-hotcorners"
    rcfile = cfgdir + "/bl-hotcornersrc"
    try:
        with open(rcfile) as cfgfile:
            config.read(rcfile)
    except FileNotFoundError:
        config.add_section(CONFIG_SECTION)
        config.set(CONFIG_SECTION, BOTTOM_LEFT, "")
        config.set(CONFIG_SECTION, BOTTOM_RIGHT, "")
        config.set(CONFIG_SECTION, TOP_LEFT, "gmrun")
        config.set(CONFIG_SECTION, TOP_RIGHT, "")
        if not os.path.exists(cfgdir):
            os.makedirs(cfgdir)
        with open(rcfile, "w") as cfgfile:
            config.write(cfgfile)
    
    # should come from the config file
    # should also be cached behind a ttl cache
    return dict(config[CONFIG_SECTION].items())


def fire_action(action):
    print(f"Firing action: {action}")
    # os.system("(" + action + ") &")


def run_poller():
    check_intervall = 0.2
    dims_output = subprocess.check_output(["xdotool", "getdisplaygeometry"]).decode().strip()
    width, height = [int(x) for x in dims_output.split()]
    rt = width - 1
    bt = height - 1

    bounce = 40  # this is used to move back towards the center of the screen
    disp = display.Display()
    root = display.Display().screen().root

    def mousepos():
        data = root.query_pointer()._data
        return data["root_x"], data["root_y"]

    def mousemove(x, y):
        fake_input(disp, X.MotionNotify, x=x, y=y)
        disp.sync()

    pos_to_name = {
        (0, 0): TOP_LEFT,
        (rt, 0): TOP_RIGHT,
        (0, bt): BOTTOM_LEFT,
        (rt, bt): BOTTOM_RIGHT,
    }

    def move_towards_center():
        # move the mouse back towards the center of the screen
        oldx, oldy = x, y = mousepos()
        bool_to_sign = {True: bounce, False: -bounce}
        x += bool_to_sign[2 * x < width]
        y += bool_to_sign[2 * y < height]
        print(f"Moving from ({oldx}, {oldy}) to ({x}, {y})")
        mousemove(x, y)

    while True:
        # do we need to refresh the config file every sleep interval?
        # seems excessive
        action_map = get_action_map()
        time.sleep(check_intervall)
        pos = mousepos()
        corner = pos_to_name.get(pos)
        action = action_map.get(corner)
        if action:
            fire_action(action)
            move_towards_center()


def get_args():
    ap = argparse.ArgumentParser(description="Hotcorners")
    ap.add_argument("-k", "--kill", help="attempt to kill any runnng instances", action="store_true")
    ap.add_argument(
        "-d",
        "--daemon",
        help="run daemon and listen for cursor triggers",
        action="store_true",
    )
    return vars(ap.parse_args())


def main():
    opts = get_args()

    if opts["kill"]:
        kill_running_instances()
    elif opts["daemon"]:
        run_poller()
    else:
        print("No arguments given. Exiting...")
        exit()


if __name__ == "__main__":
    main()
