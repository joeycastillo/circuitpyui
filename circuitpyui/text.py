import displayio
from .core import View
from adafruit_display_text.label import Label
from adafruit_display_shapes.roundrect import RoundRect
from adafruit_display_shapes.rect import Rect

class Label(displayio.Group):
    """a group that displays some text. NOT a View; cannot participate in responder chains.
    :param x: The x position of the label.
    :param y: The y position of the label.
    :param width: The width of the label in pixels.
    :param height: The height of the label in pixels.
    :param color: The text color.
    :param text: Optional. Text for the label.
    :param max_glyphs: Optional. Max glyphs for label. In case you plan to change the text later."""
    def __init__(
        self,
        x,
        y,
        width,
        height,
        font,
        *,
        color=0xFFFFFF,
        line_spacing=1,
        scale=1,
        text=None,
        max_glyphs=None,
    ):
        super().__init__(max_size=2)
        if not max_glyphs and not text:
            raise RuntimeError("Please provide a max size, or initial text")
        if not max_glyphs:
            max_glyphs = len(text)
        super().__init__(max_size=1, scale=1)
        self.local_group = displayio.Group(max_size=max_glyphs + 1, scale=scale)
        self.append(self.local_group)
        self.x = x
        self.y = y
        self.width = width
        self.height = height
        self._text = None
        self.color = color

        self.palette = displayio.Palette(2)
        self.palette.make_transparent(0)
        self.palette[1] = color

        self._scale = scale
        self._line_spacing = line_spacing

        self.font = font
        self._layout_end = 0

        if text:
            self._update_text(text)

    def _update_text(self, new_text):
        # NOTE: lots of items still TODO in here, just wanted to get it checked in.
        word_range = slice(0, 0)
        direction = 1
        char_height = self.font.get_bounding_box()[1]
        line_height = int(char_height * self._line_spacing)
        text_length = len(new_text)
        word_width = 0
        plot_word = False
        tx = 0 # "typesetter x", provisional x position of glyph when unsure whether we will wrap
        x = 0
        y = char_height
        i = 0
        layout_end = 0
        while len(self.local_group):
            self.local_group.pop()
        for i in range(0, text_length):
            character = new_text[i]
            whitespace = character == ' ' # TODO: more robust check for word wrap opportunity
            newline = character == '\n'
            if whitespace or newline or i == text_length - 1:
                plot_word = True
            glyph = self.font.get_glyph(ord(character))
            if not glyph:
                glyph = self.replacement_glyph
            try:
                ltr = glyph.ltr
                rtl = glyph.rtl
                mirrored = glyph.mirrored
            except:
                ltr = True
                rtl = False
                mirrored = False
            if direction == -1 and glyph.mirrored:
                glyph = self.font.get_glyph(glyph.mirrored)
            if rtl and direction == 1:
                if x != 0:
                    y += line_height
                x = tx = self.width - glyph.width
                direction = -1
            elif ltr and direction == -1:
                if x != self.width:
                    y += line_height
                x = tx = 0
                direction = 1
            tx += glyph.shift_x * direction
            word_width += glyph.shift_x * direction
            if tx > self.width // self._scale or x < 0:
                y += line_height
                if y > self.height:
                    break
                x = 0 if direction == 1 else self.width
                tx = word_width if direction == 1 else (self.width - word_width)
            word_range = slice(word_range.start, word_range.stop + 1)
            if plot_word:
                plot_word = False
                position_y = y - glyph.height - glyph.dy
                position_x = x + glyph.dx * direction
                for character in new_text[word_range]:
                    if character == '\n': # TODO: skip all control chars, not just newline
                        continue
                    glyph = self.font.get_glyph(ord(character))
                    if not glyph:
                        glyph = self.replacement_glyph
                    position_y = y - glyph.height - glyph.dy
                    position_x = x + glyph.dx * direction
                    if glyph.width > 0 and glyph.height > 0:
                        face = displayio.TileGrid(glyph.bitmap, pixel_shader=self.palette,
                                                  default_tile=glyph.tile_index,
                                                  tile_width=glyph.width, tile_height=glyph.height,
                                                  x=position_x, y=position_y)
                        self.local_group.append(face)
                    x += glyph.shift_x * direction
                    word_range = slice(word_range.stop, word_range.stop)
                    word_width = 0
                    layout_end = i + 1
                if newline:
                    y += line_height
                    if y > self.height:
                        break
                    x = 0 if direction == 1 else self.width
        self._layout_end = layout_end
        while len(self.local_group) > i + 1:
            self.local_group.pop()
        self._text = new_text

    @property
    def text(self):
        """Text to display."""
        return self._text

    @text.setter
    def text(self, new_text):
        self._update_text(str(new_text))

    @property
    def font(self):
        """Font to use for text display."""
        return self._font

    @font.setter
    def font(self, new_font):
        old_text = self._text
        self._font = new_font
        self.replacement_glyph = self._font.get_glyph(0xFFFD)
        if self.replacement_glyph is None:
            self.replacement_glyph = self._font.get_glyph(ord('?'))
        self._update_text(str(old_text))

    @property
    def scale(self):
        """Set the scaling of the label, in integer values"""
        return self._scale

    @scale.setter
    def scale(self, new_scale):
        old_text = self._text
        self._scale = new_scale
        self.local_group.scale = new_scale
        while len(self.local_group):
            self.local_group.pop()
        self._text = ""
        self._update_text(str(old_text))

    @property
    def layout_end(self):
        """The length of text that was actually laid out."""
        return self._layout_end

