from .core import Task, Event
import time
import board
from analogio import AnalogIn
from digitalio import DigitalInOut

class SleepTask(Task):
    """Very simple task that sleeps for a specified duration. Useful to pause between
    tasks or run loop invocations.
    :param sleep_duration: how long to sleep each time this task is run."""
    def __init__(self, sleep_duration=0.1):
        self.sleep_duration = sleep_duration

    def run(self, application):
        time.sleep(self.sleep_duration)

try:
    from gamepadshift import GamePadShift
    class PyGamerInput(Task):
        """Converts PyGamer joystick and gamepad inputs to events."""
        def __init__(self):
            self.joy_x = AnalogIn(board.JOYSTICK_X)
            self.joy_y = AnalogIn(board.JOYSTICK_Y)
            button_clock = DigitalInOut(board.BUTTON_CLOCK)
            button_data = DigitalInOut(board.BUTTON_OUT)
            button_latch = DigitalInOut(board.BUTTON_LATCH)
            self.buttons = GamePadShift(button_clock, button_data, button_latch)
            self.needs_clear = False

        def run(self, application):
            if self.needs_clear: # prevent a second press right after the first
                self.buttons.get_pressed()
                self.needs_clear = False
            x = self.joy_x.value
            y = self.joy_y.value
            if x < 5000:
                application.generate_event(Event.BUTTON_LEFT)
            if x > 60000:
                application.generate_event(Event.BUTTON_RIGHT)
            if y < 5000:
                application.generate_event(Event.BUTTON_UP)
            if y > 60000:
                application.generate_event(Event.BUTTON_DOWN)
            buttons = self.buttons.get_pressed()
            if not buttons:
                return
            if buttons & 1:
                application.generate_event(Event.BUTTON_B)
            if buttons & 1<<1:
                application.generate_event(Event.BUTTON_A)
            if buttons & 1<<2:
                application.generate_event(Event.BUTTON_START)
            if buttons & 1<<3:
                application.generate_event(Event.BUTTON_SELECT)
            self.needs_clear = True

except ImportError:
    pass

try:
    import adafruit_touchscreen
    class PyPortalInput(Task):
        """Passes touches on a PyPortal touchscreen to the application's main window.'"""
        def __init__(self, calibration, size):
            self.ts = adafruit_touchscreen.Touchscreen(board.TOUCH_XL,
                                                       board.TOUCH_XR,
                                                       board.TOUCH_YD,
                                                       board.TOUCH_YU,
                                                       calibration=calibration,
                                                       size=size)

        def run(self, application):
            touch = self.ts.touch_point
            if touch is not None:
                print(touch)
                application.window.handle_touch(True, touch[0], touch[1])

except ImportError:
    pass

try:
    import adafruit_focaltouch
    class FocalTouchInput(Task):
        """Passes touches from a FT6206 / FT6236 touchscreen to the application's main window.'"""
        def __init__(self, i2c):
            self.ts = adafruit_focaltouch.Adafruit_FocalTouch(i2c, debug=False)

        def run(self, application):
            if len(self.ts.touches):
                application.window.handle_touch(self.ts.touched, self.ts.touches[0]["x"], self.ts.touches[0]["y"])

except ImportError:
    pass
