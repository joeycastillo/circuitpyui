import time
import board
import neopixel_write
import digitalio
import displayio
import terminalio
from digitalio import DigitalInOut, Pull

import circuitpyui
from circuitpyui import Event
from circuitpyui.common_tasks import ButtonInput, SleepTask, EPDRefreshTask

display = board.DISPLAY
font = terminalio.FONT

colors = [[255, 255, 255],
          [0, 255, 0],
          [255, 255, 0],
          [255, 0, 0],
          [255, 0, 255],
          [0, 0, 255],
          [0, 255, 255]]

class MyApplication(circuitpyui.Application):
    """This is a very basic application with two buttons: one to toggle the Neopixels, another to change their color.
    It demonstrates creating and adding circuitpyui views, adding callbacks, and the basics of focus in button-based UI.
    This MagTag version also demonstrates creating a ButtonInput task with buttons connected directly to GPIO pins, and
    the use of an EPDRefreshTask to automatically update an e-paper display when the UI requires an update.
    """
    def __init__(self, window):
        # always call super.init to set the window
        super().__init__(window)

        # color index and light status are internal state; they get encapsulated with the Application
        self.color_index = 0
        self.light_is_on = False
        self.light_pin = digitalio.DigitalInOut(board.NEOPIXEL)
        self.light_pin.direction = digitalio.Direction.OUTPUT

        # MagTag can shut down power to the Neopixels when not in use. Set high at first to keep them powered down.
        self.power_pin = DigitalInOut(board.NEOPIXEL_POWER)
        self.power_pin.switch_to_output()
        self.power_pin.value = True

        # next we create our first button and add it as a subview.
        self.toggle_button = circuitpyui.Button(x=16, y=16, width=display.width - 32, height=(display.height - 32) // 3, text="Toggle Neopixels")
        self.window.add_subview(self.toggle_button)

        # since we have no touchscreen, the user will select an active element using the directional pad.
        # we need to set one of the views to be active in order to highlight it and create a start point for navigation.
        self.toggle_button.become_active()

        # this line attaches an action to the button. When the button receives an Event.TAPPED event, turn_light_on will be called.
        self.toggle_button.set_action(MyApplication.turn_light_on, Event.TAPPED)

        # creating the second button is similar to the first, but we won't tell it to become active.
        self.color_button = circuitpyui.Button(x=16, y=16+ 2 * (display.height - 32) // 3, width=display.width - 32, height=(display.height - 32) // 3, text="Change Color")
        self.window.add_subview(self.color_button)
        self.color_button.set_action(MyApplication.color_cycle, Event.TAPPED)

        # we need to tell the window which button should receive focus when an arrow button is pressed
        # this interface is simple: when the top button is active and we press 'down', select the bottom button.
        self.window.set_focus_targets(self.toggle_button, down=self.color_button)
        # and vice versa when the bottom button is selected and we press 'up'. all other directions will leave the selection alone.
        self.window.set_focus_targets(self.color_button, up=self.toggle_button)

        # Set up the (physical) buttons!
        left_button = DigitalInOut(board.BUTTON_A)
        left_button.switch_to_input(Pull.UP)
        up_button = DigitalInOut(board.BUTTON_B)
        up_button.switch_to_input(Pull.UP)
        down_button = DigitalInOut(board.BUTTON_C)
        down_button.switch_to_input(Pull.UP)
        right_button = DigitalInOut(board.BUTTON_D)
        right_button.switch_to_input(Pull.UP)
        # MagTag's four buttons could be used as a D-pad, but we need a select button, so this setup only allows up and down motion.
        # Right acts like PyGamer's A button, which in circuitpyui taps an element. Left acts like PyGamer's B button.
        self.add_task(ButtonInput([(up_button, False, Event.BUTTON_UP),
                                   (down_button, False, Event.BUTTON_DOWN),
                                   (left_button, False, Event.BUTTON_B),
                                   (right_button, False, Event.BUTTON_A)]))

        # EPD Refresh Task will update the screen as needed
        self.add_task(EPDRefreshTask(display))

        # and sleep task will keep us from repeatedly calling the same callback when the button is pressed.
        self.add_task(SleepTask(0.1))

        # finally, this is a displayio call! showing the window shows the whole view hierarchy that we have set up
        display.show(window)

    def turn_light_on(self, event):
        self.light_is_on = True
        self.update_lights()
        self.toggle_button.set_action(MyApplication.turn_light_off, Event.TAPPED)

    def turn_light_off(self, event):
        self.light_is_on = False
        self.update_lights()
        self.toggle_button.set_action(MyApplication.turn_light_on, Event.TAPPED)

    def color_cycle(self, event):
        self.color_index = (self.color_index + 1) % len(colors)
        self.update_lights()

    def update_lights(self):
        if self.light_is_on:
            # power Neopixels up
            self.power_pin.value = False
            # write the current color
            neopixel_write.neopixel_write(self.light_pin, bytearray(colors[self.color_index] * 4))
        else:
            # power Neopixels down
            self.power_pin.value = True

# style defaults to white on black for normal controls, with black on white (inverse) for active controls
# we still need to specify a style, as any text labels will expect a font.
style = circuitpyui.Style(font=font)

# create our window. This is the only displayio object we are going to show(); after this, we manage all
# of our UI by managing the window's subviews.
window = circuitpyui.Window(x=0, y=0, width=display.width, height=display.height, style=style)

# instantiate the application...
app = MyApplication(window)
# ...and run it! this will keep running in a loop indefinitely
app.run()
