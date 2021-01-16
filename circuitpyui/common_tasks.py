from .core import Task, Event
import time
import board
from analogio import AnalogIn
from digitalio import DigitalInOut, Direction

class SleepTask(Task):
    """Very simple task that sleeps for a specified duration. Useful to pause between
    tasks or run loop invocations.
    :param sleep_duration: how long to sleep each time this task is run."""
    def __init__(self, sleep_duration=0.1):
        self.sleep_duration = sleep_duration

    def run(self, application):
        time.sleep(self.sleep_duration)

class ButtonInput(Task):
    """Turns button presses into Events.
    :param buttons: an array of triples, (pin, level, event), specifying a DigitalInOut
    instance for the pin connected to the button, the logic level of the button's active
    state (True or False), and the event that should be triggered when the pin goes to
    the desired state. For example: ```
    button = DigitalInOut(board.D5)
    button.switch_to_input(Pull.UP)
    task = ButtonTask([(button, False, Event.BUTTON_SELECT)])```"""
    def __init__(self, buttons):
        self.buttons = buttons

    def run(self, application):
        for button in self.buttons:
            if button[0].value == button[1]:
                application.generate_event(button[2])

class EPDRefreshTask(Task):
    """Automatically refreshes an e-paper display when the window requires an update."""
    def __init__(self, display):
        self.display = display
        self.refreshed = False

    def run(self, application):
        if application.window.needs_display:
            self.refreshed = False
        if not self.refreshed and self.display.time_to_refresh == 0:
            try:
                self.display.refresh()
                self.refreshed = True
                application.window.set_needs_display(False)
            except RuntimeError:
                pass # try again on next run loop invocation

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

    class PyBadgeInput(Task):
        """Converts PyGamer joystick and gamepad inputs to events."""
        def __init__(self):
            button_clock = DigitalInOut(board.BUTTON_CLOCK)
            button_data = DigitalInOut(board.BUTTON_OUT)
            button_latch = DigitalInOut(board.BUTTON_LATCH)
            self.buttons = GamePadShift(button_clock, button_data, button_latch)
            self.needs_clear = False

        def run(self, application):
            if self.needs_clear: # prevent a second press right after the first
                self.buttons.get_pressed()
                self.needs_clear = False
            buttons = self.buttons.get_pressed()
            if not buttons:
                return
            if buttons & 1<<7:
                application.generate_event(Event.BUTTON_LEFT)
            if buttons & 1<<4:
                application.generate_event(Event.BUTTON_RIGHT)
            if buttons & 1<<6:
                application.generate_event(Event.BUTTON_UP)
            if buttons & 1<<5:
                application.generate_event(Event.BUTTON_DOWN)
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

try:
    from touchio import TouchIn
    class TouchMatrixInput(Task):
        """Turns gestures on a PCB-based touch matrix into button events.
        :param x_channels: An array of pins (i.e. board.D0) containing the columns of the matrix, from left to right.
        :param y_channels: An array of pins containing the rows of the matrix, from top to bottom.
        """
        def __init__(self, x_channels, y_channels):
            self.x_pads = list()
            self.y_pads = list()
            self.baseline = list()
            self.start_point = None
            self.end_point = None
            self.can_tap = False
            for pin in y_channels:
                self.y_pads.append(TouchIn(pin))
                self.baseline.append(list())
            for i in range(0, len(x_channels)):
                self.x_pads.append(TouchIn(x_channels[i]))
                for j in range(0, len(self.baseline)):
                    self.baseline[j].append(None)
            for i in range(0, len(self.y_pads)):
                for j in range(0, len(self.x_pads)):
                    self.baseline[i][j] = self.y_pads[i].raw_value + self.x_pads[j].raw_value

        def run(self, application):
            x = None
            y = None
            peak = 0
            for i in range(0, len(self.y_pads)):
                for j in range(0, len(self.x_pads)):
                    val = self.y_pads[i].raw_value + self.x_pads[j].raw_value - self.baseline[i][j]
                    if val > peak:
                        peak = val
                        (x, y) = [j, i]
            if peak > 250:
                self.end_point = [x, y]
                if self.start_point is None:
                    self.start_point = [x, y]
                    self.can_tap = True
                dx = self.end_point[0] - self.start_point[0]
                dy = self.end_point[1] - self.start_point[1]
                if dx < -1:
                    application.generate_event(Event.BUTTON_LEFT)
                    self.can_tap = False
                elif dx > 1:
                    application.generate_event(Event.BUTTON_RIGHT)
                    self.can_tap = False
                elif dy < -1:
                    application.generate_event(Event.BUTTON_UP)
                    self.can_tap = False
                elif dy > 1:
                    application.generate_event(Event.BUTTON_DOWN)
                    self.can_tap = False
            elif peak < 100:
                self.start_point = self.end_point = None
                if self.can_tap and self.start_point == self.end_point:
                    application.generate_event(Event.BUTTON_A)
                    self.can_tap = False

except ImportError:
    pass

try:
    from adafruit_mcp230xx.mcp23008 import MCP23008

    class MCP23008Input(Task):
        """Turns button presses from an I2C GPIO expander into Events.
        :param i2c: the I2C bus where the expander resides.
        :param buttons: an array of triples, (pull, level, event), in order from pin 0 to
        pin 7, specifying: (1) the direction of the pin (INPUT or OUTPUT), the pull (UP or
        None), the input's active state (True or False), and the event that should be
        triggered when the pin goes to the active state. For example:
        ```task = MCP23008Input([(Pull.UP, False, Event.BUTTON_SELECT)])```
        :param address: the expander's I2C address."""
        def __init__(self, i2c, buttons, address=0x20):
            self.mcp = MCP23008(i2c, address=address)
            self.buttons = list()
            for i in range(0, len(buttons)):
                config = buttons[i]
                pin = self.mcp.get_pin(i)
                pin.direction = Direction.INPUT
                pin.pull = config[0]
                self.buttons.append((pin, config[1], config[2]))

        def run(self, application):
            for button in self.buttons:
                if button[0].value == button[1]:
                    application.generate_event(button[2])

except ImportError:
    pass

try:
    from adafruit_stmpe610 import Adafruit_STMPE610_SPI

    class STMPE610Input(Task):
        """Passes touches from a touchscreen to the application's main window.
        :param spi: the SPI bus where the expander resides.
        :param cs: the pin (i.e. board.D6) responsible for touchscreen chip select"""
        def __init__(self, bus, cs):
            self.ts = Adafruit_STMPE610_SPI(spi, DigitalInOut(cs))

        def run(self, application):
            if not self.ts.buffer_empty:
                print(self.ts.read_data())

except ImportError:
    pass

try:
    import bbq10keyboard
    class BBQ10KeyboardInput(Task):
        def __init__(self, i2c, backlight_level=0.5):
            self.kbd = bbq10keyboard.BBQ10Keyboard(i2c)
            self.kbd.backlight = backlight_level

        def run(self, application):
            if self.kbd.key_count > 0:
                key = self.kbd.key
                # handle arrow keys separately
                if key[1] in ['\x01', '\x02', '\x03', '\x04', '\x05', '\x06', '\x07', '\x11', '\x12', ]:
                    if key[0] == bbq10keyboard.STATE_PRESS:
                        if key[1] == '\x01':
                            application.generate_event(Event.BUTTON_UP)
                        if key[1] == '\x02':
                            application.generate_event(Event.BUTTON_DOWN)
                        if key[1] == '\x03':
                            application.generate_event(Event.BUTTON_LEFT)
                        if key[1] == '\x04':
                            application.generate_event(Event.BUTTON_RIGHT)
                        if key[1] == '\x05':
                            application.generate_event(Event.BUTTON_A)
                        # TODO: map four accessory buttons on keyboard FeatherWing to... some event
                    return
                event_type = Event.KEY_PRESS
                if key[0] == bbq10keyboard.STATE_LONG_PRESS:
                    event_type = Event.KEY_LONG_PRESS
                elif key[0] == bbq10keyboard.STATE_RELEASE:
                    event_type = Event.KEY_RELEASE
                application.generate_event(event_type, {"key": key[1]})

except ImportError:
    pass
