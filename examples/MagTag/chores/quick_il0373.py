# The MIT License (MIT)
#
# Copyright (c) 2019 Scott Shawcroft for Adafruit Industries LLC
#
# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included in
# all copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN
# THE SOFTWARE.
"""
`adafruit_il0373`
================================================================================

CircuitPython `displayio` driver for IL0373-based ePaper displays


* Author(s): Scott Shawcroft

Implementation Notes
--------------------

**Hardware:**

* `Adafruit 1.54" Tri-Color Display Breakout <https://www.adafruit.com/product/3625>`_
* `Adafruit 2.13" Tri-Color Display Breakout <https://www.adafruit.com/product/4086>`_
* `Adafruit Flexible 2.9" Black and White <https://www.adafruit.com/product/4262>`_
* `Adafruit Flexible 2.13" Black and White <https://www.adafruit.com/product/4243>`_
* `Adafruit 2.13" Tri-Color FeatherWing <https://www.adafruit.com/product/4128>`_

**Software and Dependencies:**

* Adafruit CircuitPython firmware (version 5+) for the supported boards:
  https://github.com/adafruit/circuitpython/releases

"""

import displayio

__version__ = "0.0.0-auto.0"
__repo__ = "https://github.com/adafruit/Adafruit_CircuitPython_IL0373.git"

_START_SEQUENCE = (
    b"\x01\x05\x03\x00\x2b\x2b\x09"  # power setting
    b"\x06\x03\x17\x17\x17"  # booster soft start
    b"\x04\x80\xc8"  # power on and wait 200 ms
    b"\x00\x01\x0f"  # panel setting. Further filled in below.
    b"\x50\x01\x37"  # CDI setting
    b"\x30\x01\x29"  # PLL set to 150 Hz
    b"\x61\x03\x00\x00\x00"  # Resolution
    b"\x82\x81\x12\x32"  # VCM DC and delay 50ms
)

_QUICK_START_SEQUENCE = (
    b"\x01\x05\x03\x00\x2b\x2b\x13"  # power setting
    b"\x06\x03\x17\x17\x17"  # booster soft start
    b"\x04\x80\xc8"  # power on and wait 200 ms
    b"\x00\x01\x3f"  # panel setting. Further filled in below.
    b"\x50\x01\x97"  # CDI setting
    b"\x30\x01\x3C"  # PLL set to 50 Hz (M = 7, N = 4)
    b"\x61\x03\x00\x00\x00"  # Resolution
    b"\x82\x81\x12\x32"  # VCM DC and delay 50ms
    # Common voltage
    b"\x20\x2a"
    b"\x40\x0A\x00\x00\x00\x01"
    b"\x00\x0b\x0b\x00\x00\x01"
    b"\x00\x05\x01\x00\x00\x01"
    b"\x00\x07\x07\x00\x00\x01"
    b"\x00\x00\x00\x00\x00\x00"
    b"\x00\x00\x00\x00\x00\x00"
    b"\x00\x00\x00\x00\x00\x00"
    # White to White
    b"\x21\x2a"
    b"\x40\x0A\x00\x00\x00\x01"
    b"\x90\x0b\x0b\x00\x00\x01"
    b"\x40\x05\x01\x00\x00\x01"
    b"\xA0\x07\x07\x00\x00\x01"
    b"\x00\x00\x00\x00\x00\x00"
    b"\x00\x00\x00\x00\x00\x00"
    b"\x00\x00\x00\x00\x00\x00"
    # Black to White
    b"\x22\x2a"
    b"\x40\x0A\x00\x00\x00\x01"
    b"\x90\x0b\x0b\x00\x00\x01"
    b"\x40\x05\x01\x00\x00\x01"
    b"\xA0\x07\x07\x00\x00\x01"
    b"\x00\x00\x00\x00\x00\x00"
    b"\x00\x00\x00\x00\x00\x00"
    b"\x00\x00\x00\x00\x00\x00"
    # White to Black
    b"\x23\x2a"
    b"\x80\x0A\x00\x00\x00\x01"
    b"\x90\x0b\x0b\x00\x00\x01"
    b"\x80\x05\x01\x00\x00\x01"
    b"\x50\x07\x07\x00\x00\x01"
    b"\x00\x00\x00\x00\x00\x00"
    b"\x00\x00\x00\x00\x00\x00"
    b"\x00\x00\x00\x00\x00\x00"
    # Black to Black
    b"\x24\x2a"
    b"\x80\x0A\x00\x00\x00\x01"
    b"\x90\x0b\x0b\x00\x00\x01"
    b"\x80\x05\x01\x00\x00\x01"
    b"\x50\x07\x07\x00\x00\x01"
    b"\x00\x00\x00\x00\x00\x00"
    b"\x00\x00\x00\x00\x00\x00"
    b"\x00\x00\x00\x00\x00\x00"
)

_STOP_SEQUENCE = (
    b"\x50\x01\x17"  # CDI setting
    b"\x82\x01\x00"  # VCM DC to -0.10 V
    b"\x02\x00"  # Power off
)
# pylint: disable=too-few-public-methods
class IL0373(displayio.EPaperDisplay):
    r"""IL0373 driver

    :param bus: The data bus the display is on
    :param bool swap_rams: Color and black rams/commands are swapped
    :param \**kwargs:
        See below

    :Keyword Arguments:
        * *width* (``int``) --
          Display width
        * *height* (``int``) --
          Display height
        * *rotation* (``int``) --
          Display rotation
        * *color_bits_inverted* (``bool``) --
          Invert color bit values
        * *black_bits_inverted* (``bool``) --
          Invert black bit values
    """

    def __init__(self, bus, swap_rams=False, **kwargs):
        start_sequence = bytearray(_QUICK_START_SEQUENCE)

        width = kwargs["width"]
        height = kwargs["height"]
        if "rotation" in kwargs and kwargs["rotation"] % 180 != 0:
            width, height = height, width
        start_sequence[26] = width & 0xFF
        start_sequence[27] = (height >> 8) & 0xFF
        start_sequence[28] = height & 0xFF
        if swap_rams:
            color_bits_inverted = kwargs.pop("color_bits_inverted", False)
            write_color_ram_command = 0x10
            black_bits_inverted = kwargs.pop("black_bits_inverted", True)
            write_black_ram_command = 0x13
        else:
            write_black_ram_command = 0x10
            write_color_ram_command = 0x13
            color_bits_inverted = kwargs.pop("color_bits_inverted", True)
            black_bits_inverted = kwargs.pop("black_bits_inverted", False)
        if "highlight_color" not in kwargs:
            start_sequence[17] |= 1 << 4  # Set BWR to only do black and white.

        # Set the resolution to scan
        if width > 128:
            start_sequence[17] |= 0b11 << 5  # 160x296
        elif height > 252 or width > 96:
            start_sequence[17] |= 0b10 << 5  # 128x296
        elif height > 230:
            start_sequence[17] |= 0b01 << 5  # 96x252
        else:
            pass  # 0b00 is 96x230

        super().__init__(
            bus,
            start_sequence,
            _STOP_SEQUENCE,
            **kwargs,
            ram_width=160,
            ram_height=296,
            busy_state=False,
            write_black_ram_command=write_black_ram_command,
            write_color_ram_command=write_color_ram_command,
            black_bits_inverted=black_bits_inverted,
            color_bits_inverted=color_bits_inverted,
            refresh_display_command=0x12,
        )