import board
import displayio
import terminalio
import busio
from digitalio import DigitalInOut, Pull
import adafruit_display_text
import circuitpyui
from circuitpyui.common_tasks import ButtonInput, SleepTask, EPDRefreshTask
from quick_il0373 import IL0373

displayio.release_displays()
spi = busio.SPI(board.EPD_SCK, board.EPD_MOSI)
display_bus = displayio.FourWire(spi, command=board.EPD_DC, chip_select=board.EPD_CS, reset=board.EPD_RESET, baudrate=1000000)
display = IL0373(display_bus, width=296, height=128, rotation=270, seconds_per_frame=0.1, busy_pin=board.EPD_BUSY, black_bits_inverted=True, swap_rams=True)

button_padding = 4
button_height = 20
text_height=12
font = terminalio.FONT

class MyApplication(circuitpyui.Application):
    def __init__(self, window):
        super().__init__(window)

        self.availble_chores = ["Do Dishes", "Water Plants", "Sweep Floors", "Unload Dishwasher", "Clean Kitchen"]
        self.active_chores = []

        self.main_view = circuitpyui.View(x=0, y=0, width=display.width, height=display.height)
        self.window.add_subview(self.main_view)
        title_label = adafruit_display_text.label.Label(font, x=0, y=text_height // 2, text="Chore Tracker", scale=2)
        self.main_view.append(title_label)
        self.chores_label = adafruit_display_text.label.Label(font, x=0, y=text_height * 2 + text_height // 2, max_glyphs=512)
        self.main_view.append(self.chores_label)

        # virtual buttons!
        self.buttons = []
        titles = ["Add Chore", "Finish Chore"]
        for title in titles:
            button = circuitpyui.Button(x=button_padding // 2, y=display.height - button_height * len(titles) - 4 + len(self.buttons) * (button_height + button_padding), width=display.width - button_padding, height=button_height, text=title)
            button.set_action(MyApplication.show_table, circuitpyui.Event.TAPPED)
            self.buttons.append(button)
            self.main_view.add_subview(button)
        self.window.set_focus_targets(self.buttons[0], down=self.buttons[1])
        self.window.set_focus_targets(self.buttons[1], up=self.buttons[0])

        # physical buttons!
        left_button = DigitalInOut(board.BUTTON_A)
        left_button.switch_to_input(Pull.UP)
        up_button = DigitalInOut(board.BUTTON_B)
        up_button.switch_to_input(Pull.UP)
        down_button = DigitalInOut(board.BUTTON_C)
        down_button.switch_to_input(Pull.UP)
        right_button = DigitalInOut(board.BUTTON_D)
        right_button.switch_to_input(Pull.UP)
        self.add_task(ButtonInput([(up_button, False, circuitpyui.Event.BUTTON_UP),
                                   (down_button, False, circuitpyui.Event.BUTTON_DOWN),
                                   (left_button, False, circuitpyui.Event.BUTTON_B),
                                   (right_button, False, circuitpyui.Event.BUTTON_A)]))

        self.update_ui_state()
        self.add_task(EPDRefreshTask(display))
        self.add_task(SleepTask(0.1))
        display.show(self.window)

    def show_table(self, event):
        items = None
        handler = None
        if event.user_info["originator"] == self.buttons[0]:
            items = self.availble_chores
            handler = MyApplication.add_chore
        else:
            items = self.active_chores
            handler = MyApplication.complete_chore
        if items:
            self.window.remove_subview(self.main_view)
            self.table = circuitpyui.Table(x=0, y=0, width=display.width, height=display.height, cell_height=text_height + 4, show_navigation_buttons=True)
            self.window.add_subview(self.table)
            self.table.items = items
            self.table.set_action(handler, circuitpyui.Event.TAPPED)

    def hide_table(self):
        self.window.remove_subview(self.table)
        self.table = None
        self.window.add_subview(self.main_view)
        self.update_ui_state()

    def add_chore(self, event):
        chore = self.availble_chores.pop(event.user_info["index"])
        self.active_chores.append(chore)
        self.hide_table()

    def complete_chore(self, event):
        chore = self.active_chores.pop(event.user_info["index"])
        self.availble_chores.append(chore)
        self.hide_table()

    def update_ui_state(self):
        if len(self.active_chores) == 0:
            self.chores_label.text = "No chores!"
        else:
            self.chores_label.text = "\n".join(self.active_chores)
        self.buttons[0].become_active()

style = circuitpyui.Style(font=font)
window = circuitpyui.Window(x=0, y=0, width=display.width, height=display.height, style=style)
app = MyApplication(window)

app.run()