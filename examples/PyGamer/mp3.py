# inspired by / VU visualization based on Jeff Epler's JEplayer:
# https://learn.adafruit.com/pygamer-mp3-player-with-circuitpython?view=all

import gc
import os
import random
import time

import adafruit_bitmap_font.bitmap_font
import adafruit_display_text.label
from adafruit_progressbar import ProgressBar
import adafruit_imageload
import adafruit_sdcard
import analogjoy
import audioio
import audiomp3
import board
import busio
import digitalio
import displayio
import terminalio
import neopixel
import storage
from micropython import const

import circuitpyui
from circuitpyui.common_tasks import PyGamerInput

display = board.DISPLAY

BUTTON_PADDING = 2
BUTTON_HEIGHT = 20
BAR_HEIGHT = 8
BAR_PADDING = 3
FONT = adafruit_bitmap_font.bitmap_font.load_font("miniset.bdf") # terminalio.FONT for PyPortal
TEXT_HEIGHT = 8 # 12 for PyPortal

class PlayerTask(circuitpyui.Task):
    def __init__(self):
        super().__init__()
        self.pixels = neopixel.NeoPixel(board.NEOPIXEL, 5)
        self._rms = 0

    def run(self, application):
        if gc.mem_free() < 4096:
            gc.collect()

        value = application.decoder.rms_level if application.speaker.playing else 0
        self.pixels[0] = (0, 20, 0)  if value >  20 else (0, 0, 0)
        self.pixels[1] = (0, 20, 0)  if value >  40 else (0, 0, 0)
        self.pixels[2] = (0, 20, 0)  if value >  80 else (0, 0, 0)
        self.pixels[3] = (20, 20, 0) if value > 160 else (0, 0, 0)
        self.pixels[4] = (20, 0, 0)  if value > 320 else (0, 0, 0)
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
        self.speaker = audioio.AudioOut(board.SPEAKER, right_channel=board.A1)
        self.decoder = audiomp3.MP3Decoder(open("blank.mp3", "rb"))
        self.file_size = None
        self.speaker.play(self.decoder)

        # set up application state
        self.files = playlist = sorted([f for f in os.listdir("/sd/lars/") if f.lower().endswith('.mp3') and not f.startswith('.')])
        self._is_playing = False
        self.active_track = None

        # set up UI
        table_height = display.height - 24 - BUTTON_PADDING * 2 - BAR_HEIGHT
        table = circuitpyui.Table(x=0, y=0, width=display.width, height=table_height, cell_height=TEXT_HEIGHT + 4, show_navigation_buttons=True)
        self.window.add_subview(table)
        table.items = self.files
        table.set_action(PlayerApplication.track_selected, circuitpyui.Event.TAPPED)
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
        self.window.set_focus_targets(buttons[0], right=buttons[1], up=table)
        self.window.set_focus_targets(buttons[1], left=buttons[0], right=buttons[2], up=table)
        self.window.set_focus_targets(buttons[2], left=buttons[1], up=table)
        self.window.set_focus_targets(table, down=buttons[1])
        self.progress_bar = ProgressBar(0, display.height - BAR_HEIGHT - 5 - TEXT_HEIGHT, display.width, BAR_HEIGHT, bar_color=0xFFFFFF, outline_color=0xFFFFFF, stroke=1)
        self.window.append(self.progress_bar)
        self.now_playing_label = adafruit_display_text.label.Label(FONT, x=0, y=display.height - 1 - TEXT_HEIGHT // 2, max_glyphs=128)
        self.now_playing_label.text = "Not Playing"
        self.window.append(self.now_playing_label)

        # set up input devices
        self.add_task(PyGamerInput())
        self.add_task(PlayerTask())

    @property
    def is_playing(self):
        return self._is_playing

    @is_playing.setter
    def is_playing(self, value):
        self._is_playing = value
        print(f"is_playing set to {self._is_playing}")
        if value:
            self.play_pause_button.image[0] = 1 # pause button
        else:
            self.play_pause_button.image[0] = 0 # play button

    def play_file(self, filename):
        old_stream = self.decoder.file
        full_path = f"/sd/lars/{filename}"
        self.decoder.file = open(full_path, "rb")
        if old_stream is not None:
            old_stream.close()
        self.file_size = os.stat(full_path)[6]
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
        if self.active_track is None:
            self.active_track = 0
        elif self.active_track > 0:
            self.active_track -= 1
        self.play_active_track()
        time.sleep(0.25)

    def next_track(self, event):
        if self.active_track is None:
            self.active_track = 0
        elif self.active_track < len(self.files) - 1:
            self.active_track += 1
        else:
            self.speaker.stop()
            self.is_playing = False
        self.play_active_track()
        time.sleep(0.25)

    def track_finished(self):
        if self.active_track < len(self.files) - 1:
            self.active_track += 1
            self.play_active_track()
        else:
            self.is_playing = False
            self.now_playing_label.text = "Not Playing"
            self.active_track = None

style = circuitpyui.Style(font=FONT, button_radius=5)
window = circuitpyui.Window(x=0, y=0, width=display.width, height=display.height, style=style, max_size=6)
time.sleep(1) # odd but if i omit this i sometimes get a hard crash, "Attempted heap allocation when MicroPython VM not running"
app = PlayerApplication(window)
display.show(window)
app.run()