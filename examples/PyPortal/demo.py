import time
import board
import displayio
import adafruit_imageload
import terminalio
from adafruit_display_text import label

import circuitpyui
from circuitpyui import Event
from circuitpyui.common_tasks import PyPortalInput, SleepTask

display = board.DISPLAY
font = terminalio.FONT
BUTTON_HEIGHT = 48
BUTTON_PADDING = 16

class DemoApplication(circuitpyui.Application):
    """See minimal.py for the absolute basics. This demo shows more advanced view layout, focus targets and alerts."""
    def __init__(self, window):
        super().__init__(window)
        # application state
        self.characters = ["Blinka", "Adabot", "Mho", "Minerva", "Sparky"]
        self.selected_item = 0

        # this is a plain old displayio group. you can add it to your UI with the standard append method.
        # this view will not participate in the responder chain, but it's a useful way to add static elements.
        self.window.append(label.Label(font, x=16, y=16, text="circuitpyui demo!", scale=2))

        # menu is a subview that will contain all our buttons. it serves two purposes: one, it has a position,
        # and all its subviews will lay out from that origin. Two, we can set an action on it, and it will get
        # callbacks when an event bubbles up to it.
        menu = circuitpyui.View(x=16, y=40, width=display.width, height=display.height, max_size=6)
        self.window.add_subview(menu)

        sprite_sheet, palette = adafruit_imageload.load("/cp_sprite_sheet.bmp", bitmap=displayio.Bitmap, palette=displayio.Palette)
        buttons = []
        for i in range(0, 5):
            sprite = displayio.TileGrid(sprite_sheet, pixel_shader=palette,
                                        width = 1,
                                        height = 1,
                                        tile_width = 16,
                                        tile_height = 16)
            sprite[0] = i
            button = circuitpyui.Button(x=(10 + (display.width - 40) // 2) * (i % 2), y=(BUTTON_PADDING + BUTTON_HEIGHT) * (i // 2), width=(display.width - 40) // 2, height=BUTTON_HEIGHT, image=sprite, image_size=(16,16))

            # for this demo, we are setting an action for each button. This means whenever one of these is tapped,
            # the item_selected handler will be called. But! Events don't have to be captured immediately. If these
            # buttons did not have an action for the TAPPED event, the event would bubble up to the next view, which
            # is the menu containing the buttons. Try deleting this line, and replacing it with this after the loop:
            # menu.set_action(DemoApplication.item_selected, Event.TAPPED)
            button.set_action(DemoApplication.item_selected, Event.TAPPED)
            menu.add_subview(button)
            buttons.append(button)
        self.buttons = buttons

        # the PyPortalInput task captures touches and sends them to the main window's handle_touches method.
        self.add_task(PyPortalInput(calibration=((5200, 59000), (5800, 57000)), size=(display.width, display.height)))
        # the sleep task just waits a beat between each run loop invocation.
        self.add_task(SleepTask(0.1))

    def item_selected(self, event):
        # An event comes with a user_info dict; in this case, we can fetch the view that kicked off the event,
        # and use it to determine which button was pressed. If your UI were designed to take different actions
        # depending on the button pressed, it might make sense to create different handlers for each button.
        if event.user_info["originator"] in self.buttons:
            self.selected_item = self.buttons.index(event.user_info["originator"])
        else:
            return

        # the alert here is a little different from other circuitpyui views in that you don't specify an x and y
        # coordinate, just a width and height. Alerts are modal; they take over the screen and appear centered.
        style = circuitpyui.Style(font=font, background_color=0xCE79, foreground_color=0x333333)
        alert = circuitpyui.Alert(f"Selected: \n{self.characters[self.selected_item]}",
                                  width=display.width - 80, style=style,
                                  height=display.height - 120, button_text=["OK"])
        window.add_subview(alert)
        alert.become_active()
        alert.set_action(DemoApplication.dismiss_alert, Event.TAPPED)

    def dismiss_alert(self, event):
        # there is only one button here, but if there were multiple (like Yes and No) you can use the button_index
        # from the user info dict to take the appropriate action.
        print("Alert dismissed with button at index", event.user_info["button_index"])

        # when dismissing an alert, the alert is also part of the user info dict; you can use this reference to
        # dismiss the alert by removing it from the view hierarchy.
        alert = event.user_info["alert"]
        print(event.user_info)
        alert.remove_action(Event.TAPPED)
        window.remove_subview(alert)


# let's make the buttons purple for this demo. Note that the alert will appear in green because it has its own style.
style = circuitpyui.Style(font=font, background_color=0xCE00A9)
window = circuitpyui.Window(x=0, y=0, width=display.width, height=display.height, style=style, highlight_active_responder=False, max_size=3)
app = DemoApplication(window)

display.show(window)
app.run()