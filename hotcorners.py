"""Hotcorners"""

import argparse
import configparser
import logging
import os
import shlex
import subprocess
import time

import cachetools.func
from pynput import mouse
from pynput.keyboard import Controller, Key
from Xlib import X, display
from Xlib.ext.xtest import fake_input

logger = logging.getLogger("hotcorners")

CONFIG_SECTION = "Hot Corners"

BOTTOM_LEFT = "bottom_left_corner_command"
BOTTOM_RIGHT = "bottom_right_corner_command"
TOP_LEFT = "top_left_corner_command"
TOP_RIGHT = "top_right_corner_command"


def kill_running_instances():
    logger.warning("Not implemented yet...")


@cachetools.func.ttl_cache(maxsize=1, ttl=10)
def get_action_map():
    config = configparser.ConfigParser()
    cfgdir = os.getenv("HOME") + "/.config/bl-hotcorners"
    rcfile = cfgdir + "/bl-hotcornersrc"
    try:
        with open(rcfile) as cfgfile:
            config.read(rcfile)
        logger.info("Refreshing the config (%s)...", rcfile)
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

    return dict(config[CONFIG_SECTION].items())


def get_screen_dims():
    screen = display.Display().screen()
    return screen.width_in_pixels, screen.height_in_pixels


def run_poller():
    width, height = get_screen_dims()

    rt = width - 1
    bt = height - 1

    pos_to_name = {
        (0, 0): TOP_LEFT,
        (rt, 0): TOP_RIGHT,
        (0, bt): BOTTOM_LEFT,
        (rt, bt): BOTTOM_RIGHT,
    }

    bounce = 200  # this is used to move back towards the center of the screen
    disp = display.Display()
    processes = []

    keyboard = Controller()

    armed = set()

    def fire_action(action):
        logger.info("Firing action: %s ...", action)
        p = subprocess.Popen(
            shlex.split(action),
        )
        processes.append(p)

    def mousemove(x, y):
        fake_input(disp, X.MotionNotify, x=x, y=y)
        disp.sync()

    def move_towards_center(pos):
        # move the mouse back towards the center of the screen
        oldx, oldy = x, y = pos
        bool_to_sign = {True: bounce, False: -bounce}
        x += bool_to_sign[2 * x < width]
        y += bool_to_sign[2 * y < height]
        logger.info("Moving from (%d, %d) to (%d, %d)...", oldx, oldy, x, y)
        mousemove(x, y)

    def on_move(x, y):
        if armed:
            return
        pos = (x, y)
        action_map = get_action_map()
        corner = pos_to_name.get(pos)
        if corner:
            action = action_map.get(corner)
            if action:
                fire_action(action)
                move_towards_center(pos)
            else:
                keyboard.press(Key.alt)
                with keyboard.pressed(Key.tab):
                    pass
                armed.add(1)
                time.sleep(0.1)
                mousemove(rt // 2, bt // 2)

    def on_click(*_):
        # x, y, button, pressed
        if armed:
            keyboard.release(Key.alt)
            armed.clear()

    try:
        with mouse.Listener(
            on_click=on_click,
            on_move=on_move,
        ) as listener:
            listener.join()
    except KeyboardInterrupt:
        pass


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
    logging.basicConfig(level=logging.INFO)
    opts = get_args()

    if opts["kill"]:
        kill_running_instances()
    elif opts["daemon"]:
        run_poller()
    else:
        logger.warning("No arguments given. Exiting...")


if __name__ == "__main__":
    main()
