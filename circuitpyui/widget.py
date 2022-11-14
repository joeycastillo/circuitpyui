import displayio
from .core import Event, Task, Application, Style, View, Window
from adafruit_display_text.label import Label
from adafruit_display_shapes.roundrect import RoundRect
from adafruit_display_shapes.rect import Rect

class Button(View):
    """a View that draws an outline and shows either an image or a text label.
    :param x: The x position of the view.
    :param y: The y position of the view.
    :param width: The width of the view in pixels.
    :param height: The height of the view in pixels.
    :param style: a Style object defining the Button's appearance, or None to fall back to the Window's appearance.
    :param text: Optional text for a label. If you specify text, the bitmap parameter will be ignored.
    :param image: Optional, a TileGrid to display in the button. Will be ignored if text was also provided.
                  Ideally 1-bit, since we'll try to apply a two-color palette with the provided color.
    :param image_size: Temporary API, I don't think there's a way to query the TileGrid's size, so provide it here as a tuple.
    """
    def __init__(
        self,
        *,
        x=0,
        y=0,
        width=0,
        height=0,
        style=None,
        text=None,
        image=None,
        image_size=None,
    ):
        super().__init__(x=x, y=y, width=width, height=height, style=style)
        self.x = x
        self.y = y
        self.width = width
        self.height = height
        self.background = None
        self.image = image
        self.image_size = image_size
        self.text = text

    def moved_to_window(self):
        if self.text is not None:
            self.label = Label(self.style.font, x=0, y=0, text=self.text)
            self.image = None
            dims = self.label.bounding_box
            self.label.x = (self.width - dims[2]) // 2
            self.label.y = self.height // 2
            self.append(self.label)
        elif self.image is not None:
            self.label = None
            self.image.x = (self.width - self.image_size[0]) // 2
            self.image.y = (self.height - self.image_size[1]) // 2
            self.append(self.image)
        self._update_appearance(False)

    def _update_appearance(self, active):
        if active:
            if self.background is not None:
                self.remove(self.background)
            self.background = RoundRect(0, 0, self.width, self.height, r=self.style.button_radius, fill=self.style.active_background_color, outline=self.style.active_foreground_color)
            self.insert(0, self.background)
            if self.label is not None:
                self.label.color = self.style.active_foreground_color
            if self.image is not None:
                palette = displayio.Palette(2)
                palette[0] = self.style.active_foreground_color
                palette[1] = self.style.active_background_color
                self.image.pixel_shader = palette
        else:
            if self.background is not None:
                self.remove(self.background)
            self.background = RoundRect(0, 0, self.width, self.height, r=self.style.button_radius, fill=self.style.background_color, outline=self.style.foreground_color)
            self.insert(0, self.background)
            if self.label is not None:
                self.label.color = self.style.foreground_color
            if self.image is not None:
                palette = displayio.Palette(2)
                palette[0] = self.style.foreground_color
                palette[1] = self.style.background_color
                self.image.pixel_shader = palette

    def will_become_active(self, event=None):
        if not self.window.highlight_active_responder:
            return
        else:
            self._update_appearance(True)
        self.window.set_needs_display()

    def will_resign_active(self, event=None):
        if not self.window.highlight_active_responder:
            return
        else:
            self._update_appearance(False)
        self.window.set_needs_display()

class Cell(View):
    """A ``Cell`` is a specialized view intended for use with a table or grid view. Comes with one label.
    Eventually hope to add additional styles that support more labels or accessory views.
    :note: at this time a background is only drawn on the active row; other rows respect style.foreground_color,
           but style.background_color is ignored.
    :param font: The font for the label.
    :param x: The x position of the view.
    :param y: The y position of the view.
    :param width: The width of the view in pixels.
    :param height: The height of the view in pixels.
    :param style: a Style object defining the Cell's appearance, or None to fall back to the Cell's appearance.
    :param text: Text for the label.
    :param selection_style: Sets the appearance of the cell when it is the active view.
    """
    def __init__(
        self,
        *,
        x=0,
        y=0,
        width=0,
        height=0,
        style=None,
        selection_style=None,
        text="",
    ):
        super().__init__(x=x, y=y, width=width, height=height, style=style)
        self.text = text
        self.selection_style = selection_style

    def moved_to_window(self):
        self.label = Label(self.style.font, x=self.style.content_insets[3], y=self.height // 2, color=self.style.foreground_color, text=self.text)
        if self.selection_style == Table.SELECTION_STYLE_HIGHLIGHT:
            # quick hack, center previous/next buttons
            # TODO: add alignment to the Style class
            dims = self.label.bounding_box
            self.label.x = (self.width - dims[2]) // 2
            self.label.y = self.height // 2
        self.selection_style = self.selection_style
        self.append(self.label)

    def will_become_active(self, event=None):
        if self.selection_style is None:
            return
        elif self.selection_style == Table.SELECTION_STYLE_HIGHLIGHT:
            self.background = Rect(0, 0, self.width, self.height, fill=self.style.active_background_color, outline=self.style.active_background_color)
            self.insert(0, self.background)
            self.label.color = self.style.active_foreground_color
        elif self.selection_style == Table.SELECTION_STYLE_INDICATOR:
            self.background = Rect(16, 0, 8, self.height, fill=self.style.active_background_color, outline=self.style.active_background_color)
            self.append(self.background)
        self.window.set_needs_display()

    def will_resign_active(self, event=None):
        if self.selection_style is None:
            return
        if self.background is not None:
            self.remove(self.background)
        if self.selection_style == Table.SELECTION_STYLE_HIGHLIGHT:
            self.label.color = self.style.foreground_color
        self.window.set_needs_display()

class Table(View):
    SELECTION_STYLE_HIGHLIGHT = const(1)
    SELECTION_STYLE_INDICATOR = const(2)
    PAGE_WILL_CHANGE = const(10000)
    PAGE_DID_CHANGE = const(10001)
    """A ``Table`` manages a group of ``Cell``s, displaying as many as will fit in the view's display area.
    If there is more than one screen's worth of content, an on-screen previous/next page button can be added
    (for touchscreen interfaces) or the table can respond to previous/next events (button-based interface).
    :param font: The font for the cells.
    :param x: The x position of the view.
    :param y: The y position of the view.
    :param width: The width of the view in pixels.
    :param height: The height of the view in pixels.
    :param style: a Style object defining the Table's appearance, or None to fall back to the Window's appearance.
    :param indent: Temporary API; cell indent from the left. Will eventually become a proper inset.
    :param cell_height: The height of each row in the table.
    :param selection_style: Sets the appearance of cell that is the active view, or None for no indication.
    :param show_navigation_buttons: True to show previous/next buttons on screen. Useful for touch interfaces,
                                    or if the device does not have dedicated physical buttons for previous/next.
    """
    def __init__(
        self,
        *,
        x=0,
        y=0,
        width=0,
        height=0,
        style=None,
        cell_height=32,
        selection_style=SELECTION_STYLE_HIGHLIGHT,
        show_navigation_buttons=False,
    ):
        max_cells = height // cell_height
        super().__init__(x=x, y=y, width=width, height=height, style=style)
        self.cell_height = cell_height
        self.selection_style = selection_style
        self.show_navigation_buttons = show_navigation_buttons
        self._items = []
        self._add_buttons = False
        self._start_offset = 0
        self._cells_per_page = max_cells

    @property
    def items(self):
        return self._items

    @items.setter
    def items(self, items):
        self._items = items
        max_cells = self.height // self.cell_height
        num_cells = min(len(self._items), max_cells)
        if len(self._items) > num_cells and self.show_navigation_buttons:
            num_cells -= 1 # last row reserved for prev/next
            self._add_buttons = True
        else:
            self._add_buttons = False
        self._cells_per_page = num_cells
        self.update_cells()

    def update_cells(self):
        for i in range(len(self)-1, -1, -1):
            self.remove_subview(self[i])

        end = self._start_offset + self._cells_per_page
        if end > len(self._items):
            end = len(self._items)
        for i in range(0, end - self._start_offset):
            cell = Cell(x=0, y=i * self.cell_height, width=self.width, height=self.cell_height,
            style=self._style, selection_style=self.selection_style if self.window.highlight_active_responder else None, text=self._items[self._start_offset + i])
            self.add_subview(cell)
        if self._add_buttons:
            for i in range(0, 2):
                cell = Cell(x=i * self.width // 2, y=self._cells_per_page * self.cell_height, width=self.width // 2, height=self.cell_height,
                selection_style=Table.SELECTION_STYLE_HIGHLIGHT if self.window.highlight_active_responder else None, text="Previous" if i is 0 else "Next")
                self.add_subview(cell)
        if self[0] is not None:
            self[0].become_active()

    def previous_page(self):
        self.handle_event(Event(Table.PAGE_WILL_CHANGE, {"offset" : -1}))
        if self._start_offset > 0:
            self._start_offset -= self._cells_per_page
            self.update_cells()
            if self._add_buttons:
                self[len(self) - 2].become_active()
        self.handle_event(Event(Table.PAGE_DID_CHANGE, {"offset" : -1}))

    def next_page(self):
        self.handle_event(Event(Table.PAGE_WILL_CHANGE, {"offset" : 1}))
        if self._start_offset + self._cells_per_page < len(self.items):
            self._start_offset += self._cells_per_page
            self.update_cells()
            if self._add_buttons:
                self[len(self) - 1].become_active()
        self.handle_event(Event(Table.PAGE_DID_CHANGE, {"offset" : 1}))

    def handle_event(self, event=None):
        if event.event_type == Event.TAPPED:
            originator = event.user_info["originator"]
            try:
                cell_index = self.index(originator)
            except ValueError:
                return False # we could not handle this event, do not forward
            if self._add_buttons:
                if cell_index == len(self) - 1:
                    self.next_page()
                    return True
                elif cell_index == len(self) - 2:
                    self.previous_page()
                    return True
            selected_index = self._start_offset + cell_index
            event.user_info["index"] = selected_index
            # do not return True; let the event bubble up with the extra context of the selected row
        elif event.event_type == Event.BUTTON_PREV:
            self.previous_page()
            return True
        elif event.event_type == Event.BUTTON_NEXT:
            self.next_page()
            return True
        elif event.event_type in [Event.BUTTON_DOWN, Event.BUTTON_UP, Event.BUTTON_LEFT, Event.BUTTON_RIGHT]:
            try:
                cell_index = self.index(self.window.active_responder)
            except ValueError:
                return False
            if self._add_buttons:
                # special case for navigation buttons, we should be able to move left and right between them
                if event.event_type == Event.BUTTON_LEFT and cell_index == len(self) - 1:
                    self[len(self) - 2].become_active()
                    return True
                elif event.event_type == Event.BUTTON_RIGHT and cell_index == len(self) - 2:
                    self[len(self) - 1].become_active()
                    return True
                elif event.event_type == Event.BUTTON_UP and cell_index == len(self) - 1:
                    self[cell_index - 2].become_active()
                    return True
            if event.event_type == Event.BUTTON_UP and cell_index > 0:
                self[cell_index - 1].become_active()
                return True
            elif event.event_type == Event.BUTTON_DOWN and cell_index < len(self) - 2:
                self[cell_index + 1].become_active()
                return True
        return super().handle_event(event)

    def did_become_active(self, event=None):
        """NOTE: Do not call this until after you have added items, or you will get an IndexError."""
        if event is not None:
            if event.event_type == Event.BUTTON_UP:
                # special case: if user is pressing 'up', highlight the last item in the list
                self[len(self) - 1].become_active()
                return
        self[0].become_active()

class Alert(View):
    """An ``Alert`` is a modal dialog that takes over the user's screen. It can have multiple buttons for response.
    Useful to inform the user of an error condition or seek confirmation of an action. Create the alert, then set
    an action for TAPPED events on the alert. You will get an Event.TAPPED with the following items in user_info:
        * button_index: the index of the button that the user pressed to dismiss the alert.
        * alert: the alert itself.
    To dismiss the alert, remove it from the view hierarchy, either from your tapped action or in some other manner.
    :param font: The font for the alert.
    :param text: The text for the alert.
    :param width: The width of the alert in pixels.
    :param height: The height of the alert in pixels. The alert will be automatically centered on the screen.
    :param color: The foreground color for the alert.
    :param button_text: An array of strings with button titles. Try to keep this to one or two (they get narrower).
    """
    def __init__(
        self,
        text,
        *,
        width=0,
        height=0,
        style=None,
        button_text=[]
    ):
        super().__init__(x=0, y=0, width=0, height=0, style=style)
        self.text = text
        self.button_text = button_text
        self.alert_width = width
        self.alert_height = height

    def moved_to_window(self):
        self.width = self.window.width
        self.height = self.window.height
        x = (self.width - self.alert_width) // 2
        y = (self.height - self.alert_height) // 2
        self.background = RoundRect(x, y, self.alert_width, self.alert_height, r=self.style.container_radius, fill=self.style.background_color, outline=self.style.foreground_color)
        self.append(self.background)
        if len(self.button_text) == 0:
            self.label = Label(self.style.font, x=x + 8, y=y + (self.alert_height // 2), color=self.style.foreground_color, text=self.text)
        else:
            self.label = Label(self.style.font, x=x + 8, y=y + (self.alert_height // 2) - 16, color=self.style.foreground_color, text=self.text)
        self.append(self.label)
        self.buttons = []
        for i in range(0, len(self.button_text)):
            button = Button(x=x + 8 + i * (self.alert_width - 8) // len(self.button_text), y=y + self.alert_height - 32,
                            width=(self.alert_width - 8) // len(self.button_text) - 8, height=24, style=self._style, text=self.button_text[i])
            self.buttons.append(button)
            self.add_subview(button)

    def did_become_active(self, event=None):
        if len(self.buttons):
            self.buttons[0].become_active()

    def handle_event(self, event=None):
        if event.event_type == Event.TAPPED:
            originator = event.user_info["originator"]
            if originator == self:
                return False # alert catches all touches that aren't buttons. don't let user escape the modal.
            event.user_info["button_index"] = self.buttons.index(originator)
        try:
            active_index = self.buttons.index(self.window.active_responder)
        except ValueError:
            return False # we could not handle this event, do not forward
        event.user_info["alert"] = self
        if event.event_type == Event.BUTTON_LEFT:
            if active_index > 0:
                self.buttons[active_index - 1].become_active()
                return True
            else:
                return False # do not forward up the chain; user cannot escape modal
        elif event.event_type == Event.BUTTON_RIGHT:
            if active_index < len(self.buttons) - 1:
                self.buttons[active_index + 1].become_active()
                return True
            else:
                return False # do not forward up the chain; user cannot escape modal
        return super().handle_event(event)
