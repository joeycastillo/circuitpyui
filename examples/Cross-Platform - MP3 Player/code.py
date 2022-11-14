# inspired by and VU visualization based on Jeff Epler's JEplayer:
# https://learn.adafruit.com/pygamer-mp3-player-with-circuitpython?view=all
import gc
import os
import random
import time

import adafruit_bitmap_font.bitmap_font
import adafruit_display_text.label
from adafruit_progressbar.ProgressBar import ProgressBar
import adafruit_imageload
import adafruit_sdcard
import audioio
import audiomp3
import board
import busio
import digitalio
import displayio
import terminalio
import neopixel
import storage

import circuitpyui

display = board.DISPLAY

try:
    from circuitpyui.common_tasks import PyPortalInput
    INPUT_TASK = PyPortalInput(calibration=((5200, 59000), (5800, 57000)), size=(display.width, display.height))
    FONT = terminalio.FONT
    STYLE = circuitpyui.Style(font=FONT, button_radius=8, active_background_color=0x000000, active_foreground_color=0xFFFFFF)
    TEXT_HEIGHT = 12
    ROW_HEIGHT = 36
    BUTTON_HEIGHT = 30
except ImportError:
    pass

try:
    from circuitpyui.common_tasks import PyGamerInput
    INPUT_TASK = PyGamerInput()
    FONT = adafruit_bitmap_font.bitmap_font.load_font("miniset.bdf")
    STYLE = circuitpyui.Style(font=FONT, button_radius=5)
    TEXT_HEIGHT = 8
    ROW_HEIGHT = 20
    BUTTON_HEIGHT = 20
except ImportError:
    pass

BUTTON_PADDING = 2
BAR_HEIGHT = 8
BAR_PADDING = 3

GREEN = (0, 20, 0)
YELLOW = (20, 20, 0)
RED = (20, 0, 0)

def px(x, y):
    return 0 if x <= 0 else round(x / y)

class PlayerTask(circuitpyui.Task):
    def __init__(self):
        super().__init__()
        self.pixels = neopixel.NeoPixel(board.NEOPIXEL, 5)

    def run(self, application):
        print(gc.mem_free())
        if gc.mem_free() < 4096:
            gc.collect()

        if application.speaker.playing:
            value = application.decoder.rms_level if application.speaker.playing else 0
            self.pixels[0] = GREEN  if value >  20 else (0, px(value, 1), 0)
            self.pixels[1] = GREEN  if value >  40 else (0, px(value - 20, 1), 0)
            self.pixels[2] = GREEN  if value >  80 else (0, px(value - 40, 2), 0)
            self.pixels[3] = YELLOW if value > 160 else (px(value - 80, 4), px(value - 80, 4), 0)
            self.pixels[4] = RED    if value > 320 else (px(value - 160, 8), 0, 0)
            self.pixels.show()

        if application.file_size is not None:
            application.progress_bar.progress = application.decoder.file.tell() / application.file_size

        if application.is_playing and not application.speaker.playing:
            application.track_finished()

class PlayerApplication(circuitpyui.Application):
    def __init__(self, window):
        super().__init__(window)

        # set up sound output
        enable = digitalio.DigitalInOut(board.SPEAKER_ENABLE)
        enable.direction = digitalio.Direction.OUTPUT
        enable.value = True
        self.speaker = audioio.AudioOut(board.SPEAKER)
        self.decoder = audiomp3.MP3Decoder(open("blank.mp3", "rb"))
        self.file_size = None
        self.speaker.play(self.decoder)

        # set up storage
        spi = busio.SPI(board.SCK, MOSI=board.MOSI, MISO=board.MISO)
        sd_cs = digitalio.DigitalInOut(board.SD_CS)
        sdcard = adafruit_sdcard.SDCard(spi, sd_cs, baudrate=6000000)
        vfs = storage.VfsFat(sdcard)
        storage.mount(vfs, "/sd")

        # set up application state
        self.files = sorted([f for f in os.listdir("/sd/") if f.lower().endswith('.mp3') and not f.startswith('.')])
        self._is_playing = False
        self.active_track = None

        # set up UI
        table_height = display.height - BUTTON_PADDING - BUTTON_HEIGHT - BAR_PADDING - BAR_HEIGHT - TEXT_HEIGHT
        table = circuitpyui.Table(x=0, y=0, width=display.width, height=table_height, cell_height=ROW_HEIGHT, show_navigation_buttons=True)
        self.window.add_subview(table)
        table.items = self.files
        table.set_action(PlayerApplication.track_selected, circuitpyui.Event.TAPPED)
        table.set_action(PlayerApplication.page_will_change, circuitpyui.Table.PAGE_WILL_CHANGE)
        table.set_action(PlayerApplication.page_did_change, circuitpyui.Table.PAGE_DID_CHANGE)
        sprite_sheet, palette = adafruit_imageload.load("icons.bmp", bitmap=displayio.Bitmap, palette=displayio.Palette)
        button_width = display.width // 3 - BUTTON_PADDING
        buttons = []
        for button_index in [3, 0, 4]:
            sprite = displayio.TileGrid(sprite_sheet, pixel_shader=palette, width = 1, height = 1, tile_width = 16, tile_height = 16)
            sprite[0] = button_index
            button = circuitpyui.Button(x=BUTTON_PADDING // 2 + len(buttons) *(button_width + BUTTON_PADDING), y=display.height - BUTTON_HEIGHT - 4 - BAR_HEIGHT - BAR_PADDING - TEXT_HEIGHT, width=button_width, height=BUTTON_HEIGHT, image=sprite, image_size=(16, 16))
            buttons.append(button)
            self.window.add_subview(button)
        buttons[0].set_action(PlayerApplication.previous_track, circuitpyui.Event.TAPPED)
        buttons[1].set_action(PlayerApplication.play_pause, circuitpyui.Event.TAPPED)
        buttons[2].set_action(PlayerApplication.next_track, circuitpyui.Event.TAPPED)
        self.play_pause_button = buttons[1]

        # add focus targets
        self.window.set_focus_targets(buttons[0], right=buttons[1], up=table)
        self.window.set_focus_targets(buttons[1], left=buttons[0], right=buttons[2], up=table)
        self.window.set_focus_targets(buttons[2], left=buttons[1], up=table)
        self.window.set_focus_targets(table, down=buttons[1])

        # add non-interactive elements
        self.progress_bar = ProgressBar(0, display.height - BAR_HEIGHT - 5 - TEXT_HEIGHT, display.width, BAR_HEIGHT, bar_color=0xFFFFFF, outline_color=0xFFFFFF, stroke=1)
        self.window.append(self.progress_bar)
        self.now_playing_label = adafruit_display_text.label.Label(FONT, x=0, y=display.height - 1 - TEXT_HEIGHT // 2)
        self.now_playing_label.text = "Not Playing"
        self.window.append(self.now_playing_label)

        # set up input devices
        self.add_task(INPUT_TASK)
        self.add_task(PlayerTask())

    @property
    def is_playing(self):
        return self._is_playing

    @is_playing.setter
    def is_playing(self, value):
        self._is_playing = value
        if value:
            self.play_pause_button.image[0] = 1 # pause button
        else:
            self.play_pause_button.image[0] = 0 # play button

    def play_file(self, filename):
        if self.is_playing:
            self.speaker.stop()
        old_stream = self.decoder.file
        full_path = f"/sd/{filename}"
        self.decoder.file = open(full_path, "rb")
        if old_stream is not None:
            old_stream.close()
        self.file_size = os.stat(full_path)[6]
        gc.collect()
        self.speaker.play(self.decoder)
        self.now_playing_label.text = f"Now playing: {filename}"
        self.is_playing = True

    def play_active_track(self):
        self.play_file(self.files[self.active_track])

    def track_selected(self, event):
        self.active_track = event.user_info["index"]
        self.play_active_track()

    def play_pause(self, event):
        if self.active_track is None: # if nothing selected, start playing the playlist!
            self.active_track = 0
            self.play_active_track()
        elif self.is_playing:
            self.is_playing = False
            self.speaker.pause()
        else:
            self.is_playing = True
            self.speaker.resume()
        time.sleep(0.25)

    def previous_track(self, event):
        self.speaker.stop()
        if self.active_track is None:
            self.active_track = 0
        elif self.active_track > 0:
            self.active_track -= 1
        self.play_active_track()
        time.sleep(0.25)

    def next_track(self, event):
        self.speaker.stop()
        if self.active_track is None:
            self.active_track = 0
        elif self.active_track < len(self.files) - 1:
            self.active_track += 1
        else:
            self.is_playing = False
        self.play_active_track()
        time.sleep(0.25)

    def page_will_change(self, event):
        if self.is_playing:
            self.speaker.pause()

    def page_did_change(self, event):
        if self.is_playing:
            self.speaker.resume()

    def track_finished(self):
        if self.active_track < len(self.files) - 1:
            self.active_track += 1
            self.play_active_track()
        else:
            self.is_playing = False
            self.now_playing_label.text = "Not Playing"
            self.active_track = None

window = circuitpyui.Window(x=0, y=0, width=display.width, height=display.height, style=STYLE)
app = PlayerApplication(window)
display.show(window)
app.run()
