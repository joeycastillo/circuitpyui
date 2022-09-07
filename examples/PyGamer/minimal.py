import time
import board
import neopixel_write
import digitalio
import displayio
import terminalio

import circuitpyui
from circuitpyui import Event
from circuitpyui.common_tasks import PyGamerInput, SleepTask

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
    """
    def __init__(self, window):
        # always call super.init to set the window
        super().__init__(window)

        # color index and light status are internal state; they get encapsulated with the Application
        self.color_index = 0
        self.turn_light_on = False
        self.light_pin = digitalio.DigitalInOut(board.NEOPIXEL)
        self.light_pin.direction = digitalio.Direction.OUTPUT

        # next we create our button and add it as a subview.
        self.toggle_button = circuitpyui.Button(x=16, y=16, width=display.width - 32, height=(display.height - 32) // 3, text="Light ON", max_glyphs=len("Light ON") + 1)
        self.window.add_subview(self.toggle_button)

        # since we have no touchscreen, the user will select an active element using the directional pad.
        # we need to set one of the views to be active in order to highlight it and create a start point for navigation.
        self.toggle_button.become_active()

        # this line attaches an action to the button. when the button receives am Event.TAPPED event, turn_light_on will be called.
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

        # adding our two tasks. PyGamerInput will translate button presses and joystick motion to events.
        self.add_task(PyGamerInput())
        # and sleep task will keep us from repeatedly calling the same callback when the button is pressed.
        self.add_task(SleepTask(0.1))

        # finally, this is a displayio call! showing the window shows the whole view hierarchy that we have set up
        display.show(window)

    def turn_light_on(self, event):
        self.turn_light_on = True
        self.update_ui()

    def turn_light_off(self, event):
        self.turn_light_on = False
        self.update_ui()

    def color_cycle(self, event):
        self.color_index = (self.color_index + 1) % len(colors)
        self.update_ui()

    def update_ui(self):
        if self.turn_light_on:
            # note that we can overwrite the action for the toggle_button.
            # Now, when the button is pressed, turn_light_off will be called.
            self.toggle_button.set_action(MyApplication.turn_light_off, Event.TAPPED)

            # update neopixel bar
            neopixel_write.neopixel_write(self.light_pin, bytearray(colors[self.color_index] * 5))

            # since this is all displayio, we can just change the text here and it will update!
            # note though that if you are using an e-paper display you will still have to figure
            # out when to refresh, probab;y using the window's needs_display property.
            self.toggle_button.label.text="Light OFF"
        else:
            self.toggle_button.set_action(MyApplication.turn_light_on, Event.TAPPED)
            neopixel_write.neopixel_write(self.light_pin, bytearray([0, 0, 0] * 5))
            self.toggle_button.label.text="Light ON"

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