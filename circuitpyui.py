import displayio
from adafruit_display_text import label
from micropython import const
import adafruit_button

class Event():
    TOUCH_BEGAN = const(1)
    BUTTON_LEFT = const(100)
    BUTTON_DOWN = const(101)
    BUTTON_UP = const(102)
    BUTTON_RIGHT = const(103)
    BUTTON_SELECT = const(104)
    BUTTON_PREV = const(105)
    BUTTON_NEXT = const(106)
    BUTTON_LOCK = const(107)

    def __init__(
        self,
        event_type,
        user_info):
            self.event_type = event_type
            self.user_info = user_info

class Responder(displayio.Group):
    """Base class for ``circuitpyui`` classes. Has a position and a size.
    When initializing this class, pass in the parent responder -- usually the group you are adding the responder to --
    as next_responder. When an event is generated, the originating responder will have a chance to handle the event.
    If it does not, the event should pass to the next_responder.
    :param x: The x position of the view.
    :param y: The y position of the view.
    :param width: The width of the view in pixels.
    :param height: The height of the view in pixels.
    :param max_size: Maximum number of groups that will be added.
    """
    def __init__(
        self,
        *,
        x=0,
        y=0,
        width=0,
        height=0,
        max_size=5,
    ):
        super().__init__(x=x, y=y, max_size=max_size)
        self.x = x
        self.y = y
        self.width = width
        self.height = height
        self.next_responder = None

    def add_subview(self, view):
        """Adds a Responder to the view hierarchy. Only for ``Responder``s and their subclasses;
        if you are adding a plain displayio ``Group``, use append() instead.
        :param view: The view to add to the hierarchy."""
        view.next_responder = self
        self.append(view)
    
    def remove_subview(self, view):
        """Removes a Responder from the view hierarchy. Only for ``Responder``s and their subclasses;
        if you are removing a plain displayio ``Group``, use remove() instead.
        :param view: The view to remove from the hierarchy."""
        view.next_responder = None
        self.remove(view)

    def contains(self, x, y):
        """Used to determine if a point is contained within this responder, mostly for touch UI.
        :param point: a tuple with the x and y value.
        :return: True if the point was inside this view, False if not."""
        return (self.x <= x <= self.x + self.width) and (self.y <= y <= self.y + self.height)

    def handle_event(self, event):
        """Subclasses should override this to handle Events that are relevant to them.
        :param event: an Event class with a required event_type and an optional user_info dictionary.
        :return: True if the event was handled, False if not."""
        if self.next_responder is not None:
            return self.next_responder.handle_event(event)
        return False

    def handle_touch(self, touched, x, y):
        """When using a touch UI, call this method repeatedly to handle any touch events coming in.
        If the user touched a responder, it will emit a TOUCH_BEGAN event that can propagate through the responder chain.
        Subclasses should not need to override this method.
        :param touched: a boolean indicating whether there is a finger on the display.
        :param x: the x coordinate of the touch
        :param y: the y coordinate of the touch
        :return: the topmost view that was touched, or None if the touch fell outside of any view."""
        if not touched:
            return None # eventually maybe use this to inform touch up events?
        if not self.contains(x, y):
            return None
        for subview in reversed(self): # process frontmost layers first
            try:
                retval = subview.handle_touch(touched, x - self.x, y - self.y)
                if retval is not None:
                    return retval
            except AttributeError:
                continue # plain displayio groups can live in the view hierarchy, but they don't participate in responder chains.
        if self.contains(x, y):
            self.handle_event(Event(Event.TOUCH_BEGAN, {"x": x, "y": y, "originator" : self}))
            return self
        return None

class Window(Responder):
    """A window is the topmost view in a chain of responders. All responders should live in a tree under the window.
    In a touch environment, the window defers to Responder's ``handle_touch`` method to forward a touch to the correct responder.
    In a cursor-based environment, the window can handle pushbutton events to move focus between responders.
    :param x: The x position of the view.
    :param y: The y position of the view.
    :param width: The width of the view in pixels.
    :param height: The height of the view in pixels.
    :param max_size: Maximum number of groups that will be added.
    """
    def __init__(
        self,
        *,
        x=0,
        y=0,
        width=0,
        height=0,
        max_size=5,
    ):
        super().__init__(x=x, y=y, width=width, height=height, max_size=max_size)
        self.x = x
        self.y = y
        self.width = width
        self.height = height
        self.next_responder = None
        self.active_responder = None

    def handle_event(self, event):
        """By default, ``Window`` consumes direction pad events and the Select button, but no touches."""
        if event.event_type is Event.BUTTON_LEFT:
            # TODO: Move focus left
            return True
        if event.event_type is Event.BUTTON_RIGHT:
            # TODO: Move focus right
            return True
        if event.event_type is Event.BUTTON_UP:
            # TODO: Move focus up
            return True
        if event.event_type is Event.BUTTON_DOWN:
            # TODO: Move focus down
            return True
        if event.event_type is Event.BUTTON_SELECT and self.active_responder is not None:
            # hacky, this should not be a touch. this is just a placeholder til i think through the event system
            self.active_responder.handle_event(Event(Event.TOUCH_BEGAN, None))
            return True
        return super().handle_event(event)

class Button(Responder):
    """Temporary class, just wraps an adafruit_button for testing."""
    def __init__(
        self,
        *,
        x=0,
        y=0,
        width=0,
        height=0,
        max_size=5,
        label=None,
        font=None
    ):
        super().__init__(x=x, y=y, width=width, height=height, max_size=max_size)
        self.x = x
        self.y = y
        self.width = width
        self.height = height
        self.next_responder = None
        self.button = adafruit_button.Button(x=0, y=0,
                                             width=width,
                                             height=height,
                                             label=label,
                                             label_font=font,
                                             label_color=0x000000,
                                             fill_color=0xFFFFFF, 
                                             outline_color=0xFFFFFF,
                                             selected_fill=0xFFFFFF, 
                                             selected_outline=0x000000,
                                             selected_label=0x000000)
        self.append(self.button)

    def handle_event(self, event):
        if event.event_type == TOUCH_BEGAN:
            self.button.selected = True
            return True
        return super().handle_event(event)

class Cell(Responder):
    """A ``Cell`` is a specialized responder intended for use with a table or grid view. Comes with one label.
    You should not add additional groups to a cell; it has a max_size of 1. Eventually hope to add additional
    styles that support more labels or accessory views.
    :param font: The font for the label.
    :param x: The x position of the view.
    :param y: The y position of the view.
    :param width: The width of the view in pixels.
    :param height: The height of the view in pixels.
    :param max_glyphs: Maximum number of glyphs in the label. Optional if ``text`` is provided.
    :param text: Text for the label.
    """
    def __init__(
        self,
        font,
        *,
        x=0,
        y=0,
        width=0,
        height=0,
        max_glyphs=None,
        text="",
    ):
        super().__init__(x=x, y=y, width=width, height=height, max_size=1)
        self.label = label.Label(font, x=0, y=self.height // 2, max_glyphs=max_glyphs, text=text)
        self.append(self.label)

class Table(Responder):
    """A ``Table`` manages a group of ``Cell``s, displaying as many as will fit in the view's display area. 
    If there is more than one screen's worth of content, an on-screen previous/next page button can be added 
    (for touchscreen interfaces) or the table can respond to previous/next events (button-based interface).
    :param font: The font for the cells.
    :param x: The x position of the view.
    :param y: The y position of the view.
    :param width: The width of the view in pixels.
    :param height: The height of the view in pixels.
    :param cell_height: The height of each row in the table.
    :param show_navigation_buttons: True to show previous/next buttons on screen. Useful for touch interfaces,
                                    or if the device does not have dedicated physical buttons for previous/next.
    """
    def __init__(
        self,
        font,
        *,
        x=0,
        y=0,
        width=0,
        height=0,
        cell_height=32,
        show_navigation_buttons=False,
    ):
        max_cells = height // cell_height
        super().__init__(x=x, y=y, width=width, height=height, max_size=max_cells + (1 if show_navigation_buttons else 0))
        self.cell_height = cell_height
        self.font = font
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
            cell = Cell(self.font, x=0, y=i * self.cell_height, width=self.width, height=self.cell_height, text=self._items[self._start_offset + i])
            self.add_subview(cell)
        if self._add_buttons:
            for i in range(0, 2):
                cell = Cell(self.font, x=i * self.width // 2, y=self._cells_per_page * self.cell_height, width=self.width // 2, height=self.cell_height, text="Previous" if i is 0 else "Next")
                self.add_subview(cell)
    
    def previous_page(self):
        if self._start_offset > 0:
            self._start_offset -= self._cells_per_page
            self.update_cells()

    def next_page(self):
        if self._start_offset + self._cells_per_page < len(self.items):
            self._start_offset += self._cells_per_page
            self.update_cells()
    
    def handle_event(self, event):
        if event.event_type == Event.TOUCH_BEGAN:
            originator = event.user_info["originator"]
            try:
                cell_index = self.index(originator)
            except ValueError:
                return False # we could not handle this event, do not forward
            if self.show_navigation_buttons:
                if cell_index == len(self) - 1:
                    self.next_page()
                    return True
                elif cell_index == len(self) - 2:
                    self.previous_page()
                    return True
            selected_index = self._start_offset + cell_index
        elif event.event_type == Event.BUTTON_PREV:
            self.previous_page()
            return True
        elif event.event_type == Event.BUTTON_NEXT:
            self.next_page()
            return True
        return super().handle_event(event)
