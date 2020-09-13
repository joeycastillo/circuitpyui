import displayio
from adafruit_display_text.label import Label
from adafruit_display_shapes.roundrect import RoundRect
from micropython import const

class Event():
    TAPPED = const(1)
    TOUCH_BEGAN = const(10)
    BUTTON_LEFT = const(100)
    BUTTON_DOWN = const(101)
    BUTTON_UP = const(102)
    BUTTON_RIGHT = const(103)
    BUTTON_SELECT = const(104)
    BUTTON_PREV = const(105)
    BUTTON_NEXT = const(106)
    BUTTON_LOCK = const(107)

    def __init__(self, event_type, user_info):
        self.event_type = event_type
        self.user_info = user_info

class Task():
    def __init__(self):
        pass

    def run(self, runloop):
        pass

class RunLoop():
    """Runs a set of tasks in a loop. Each task should have one method, ``run``, that will perform whatever actions the task
    needs to do to serve its purpose. The run loop will run until a Task's ``run`` method returns True. Tasks run in the order
    added, so it would make sense to add your input tasks (i.e. collect touches and button presses) before your output tasks
    (refresh the screen, etc).
    :param window: The window associated with the run loop."""
    def __init__(self, window):
        self.window = window
        self.tasks = []

    def add_task(self, task):
        """Adds a task to the run loop.
        :param task: The task to add."""
        self.tasks.append(task)

    def remove_task(self, task):
        """Removes a task from the run loop.
        :param task: The task to remove."""
        self.tasks.remove(task)

    def run(self):
        """Repeatedly runs all tasks in the run loop. Will run until a task returns True.
        """
        while True:
            for task in self.tasks:
                if task.run(self):
                    return
                while len(self.window.event_queue):
                    (responder, event) = self.window.event_queue.pop(0)
                    responder.handle_event(event)

    def generate_event(self, event_type, user_info = None):
        """Generates an event. Tasks can call this method to create events from external inputs; for example, if the user pressed the
        "Select" button, you could generate a BUTTON_SELECT event in your button task. The window's active responder gets first crack
        at handling the event. If the active responder cannot handle the event, it will bubble up the responder chain.
        :param event_type: The type of event to generate.
        :param user_info: An optional dictionary with additional information about the event."""
        self.window.active_responder.handle_event(Event(event_type, user_info))

class Responder(displayio.Group):
    """Base class for ``circuitpyui`` classes. Has a position and a size.
    When you add a responder to another responder using ``add_subview``, it will join a chain of responders that can handle
    and pass along ``Event``s. When an event is generated, the originating responder will have a chance to handle it.
    If it does not, the event should pass to the next_responder.
    :param x: The x position of the view.
    :param y: The y position of the view.
    :param width: The width of the view in pixels.
    :param height: The height of the view in pixels.
    :param max_size: Maximum number of groups and responders that will be added.
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
        self.window = None
        self.actions = None

    def add_subview(self, view):
        """Adds a Responder to the view hierarchy. Only for ``Responder``s and their subclasses;
        if you are adding a plain displayio ``Group``, use append() instead.
        :param view: The view to add to the hierarchy."""
        view.next_responder = self
        view.window = self if self.__class__ is Window else self.window
        self.append(view)
        if view.window is not None:
            view.window.set_needs_display()

    def remove_subview(self, view):
        """Removes a Responder from the view hierarchy. Only for ``Responder``s and their subclasses;
        if you are removing a plain displayio ``Group``, use remove() instead.
        :param view: The view to remove from the hierarchy."""
        view.next_responder = None
        view.window = None
        self.remove(view)
        if self.window is not None:
            self.window.set_needs_display()

    def become_active(self):
        """Causes this view to become the active responder in the window."""
        self.window.active_responder.will_resign_active()
        self.will_become_active()
        self.window.active_responder = self

    def will_resign_active(self):
        """Called before a view resigns its status as the active responder.
        Subclasses can override this to configure their appearance in response to this event."""
        pass

    def will_become_active(self):
        """Called before a view becomes the active responder.
        Subclasses can override this to configure their appearance in response to this event."""
        pass

    def _contains(self, x, y):
        """Internal method to to determine if a point is contained within this responder, mostly for touch UI.
        :param x: the x value to test.
        :param y: the y value to test.
        :return: True if the point was inside this view, False if not."""
        return (self.x <= x <= self.x + self.width) and (self.y <= y <= self.y + self.height)

    def handle_event(self, event):
        """Subclasses should override this to handle Events that are relevant to them.
        :param event: an Event class with a required event_type and an optional user_info dictionary.
        :return: True if the event was handled, False if not."""
        if event.event_type == Event.TOUCH_BEGAN or event.event_type is Event.BUTTON_SELECT:
            self.handle_event(Event(Event.TAPPED, {"originator" : self}))
        if self.actions is not None and event.event_type in self.actions:
            self.actions[event.event_type](event)
            return True
        elif self.next_responder is not None:
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
        if not self._contains(x, y):
            return None
        for subview in reversed(self): # process frontmost layers first
            if hasattr(subview, 'handle_touch') and callable(subview.handle_touch):
                retval = subview.handle_touch(touched, x - self.x, y - self.y)
                if retval is not None:
                    return retval
        if self._contains(x, y):
            self.window.queue_event(self, Event(Event.TOUCH_BEGAN, {"x": x, "y": y, "originator" : self}))
            return self
        return None

    def set_action(self, action, event_type):
        """Adds an action that can be performed when a given event type occurs. An action should be a function taking exactly
        one parameter, the Event that triggered the action. For example, say you are implementing a Pause button. You would call
        ``pause_button.add_action(pause, Event.TAPPED)``, and now your ``pause`` function will be called whenever the user taps
        the button. Only one action can be set for a given event type; if you attempt to set an action
        :param action: The function to call when a matching event takes place.
        :param event_type: The type of event that will trigger this action."""
        if self.actions is None:
            self.actions = {}
        self.actions[event_type] = action

    def remove_action(self, event_type):
        """Removes an action for a given event type.
        :param event_type: The type of event whose action you are removing."""
        if self.actions is not None and event_type in self.actions:
            del self.actions[event_type]
        if not len(self.actions):
            self.actions = None

class Window(Responder):
    """A window is the topmost view in a chain of responders. All responders should live in a tree under the window.
    In a touch environment, the window defers to Responder's ``handle_touch`` method to forward a touch to the correct responder.
    In a cursor-based environment, the window can handle pushbutton events to move focus between responders.
    :param x: The x position of the view.
    :param y: The y position of the view.
    :param width: The width of the view in pixels.
    :param height: The height of the view in pixels.
    :param max_size: Maximum number of groups that will be added.
    :param highlight_active_responder: True to display a selection indicator on the active responder, useful for cursor-based
                                       interfaces. Pass in False if you are using a touchscreen.
    """
    def __init__(
        self,
        *,
        x=0,
        y=0,
        width=0,
        height=0,
        max_size=5,
        highlight_active_responder=True,
    ):
        super().__init__(x=x, y=y, width=width, height=height, max_size=max_size)
        self.x = x
        self.y = y
        self.width = width
        self.height = height
        self.highlight_active_responder=highlight_active_responder
        self.next_responder = None
        self.active_responder = self
        self.event_queue = []
        self.dirty = False

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
        return super().handle_event(event)

    def queue_event(self, responder, event):
        """Queues an event to be handled after the current run loop task completes. This is useful to avoid exhausting the stack;
        for example, after recursively locating the source of a touch event, we can queue the tap event so that the user's action
        doesn't get called from the bottom of that stack of calls.
        :param responder: the responder that should take first crack at handling the event.
        :param event: the event to give it."""
        self.event_queue.append((responder, event))

    def needs_display(self):
        return self.dirty

    def set_needs_display(self, needs_display = True):
        self.dirty = needs_display

class Button(Responder):
    """a Responder that draws an outline and shows either an image or a text label.
    :param x: The x position of the view.
    :param y: The y position of the view.
    :param width: The width of the view in pixels.
    :param height: The height of the view in pixels.
    :param color: The foreground color for text and button outline.
    :param text: Optional text for a label. If you specify text, the bitmap parameter will be ignored.
    :param font: Font for the label. Required if text was specified; otherwise, optional.
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
        color=0xFFFFFF,
        text=None,
        font=None,
        image=None,
        image_size=None,
    ):
        super().__init__(x=x, y=y, width=width, height=height, max_size=2)
        self.x = x
        self.y = y
        self.width = width
        self.height = height
        self.next_responder = None
        self.color = color
        self.background = None
        if text is not None:
            self.label = Label(font, x=0, y=0, color=color, text=text)
            self.image = None
            dims = self.label.bounding_box
            self.label.x = (self.width - dims[2]) // 2
            self.label.y = self.height // 2
            self.append(self.label)
        elif image is not None:
            self.label = None
            self.image = image
            self.image.x = (self.width - image_size[0]) // 2
            self.image.y = (self.height - image_size[1]) // 2
            self.append(self.image)
        self._update_appearance(False)

    def _update_appearance(self, active):
        if active:
            if self.background is not None:
                self.remove(self.background)
            self.background = RoundRect(0, 0, self.width, self.height, r=10, fill=self.color, outline=self.color)
            self.insert(0, self.background)
            if self.label is not None:
                self.label.color = ~self.color & 0xFFFFFF
            if self.image is not None:
                palette = displayio.Palette(2)
                palette[0] = ~self.color & 0xFFFFFF
                palette[1] = self.color
                self.image.pixel_shader = palette
        else:
            if self.background is not None:
                self.remove(self.background)
            self.background = RoundRect(0, 0, self.width, self.height, r=10, fill=~self.color & 0xFFFFFF, outline=self.color)
            self.insert(0, self.background)
            if self.label is not None:
                self.label.color = self.color
            if self.image is not None:
                palette = displayio.Palette(2)
                palette[0] = self.color
                palette[1] = ~self.color & 0xFFFFFF
                self.image.pixel_shader = palette
        
    def will_become_active(self):
        if not self.window.highlight_active_responder:
            return
        else:
            self._update_appearance(True)
        self.window.set_needs_display()

    def will_resign_active(self):
        if not self.window.highlight_active_responder:
            return
        else:
            self._update_appearance(False)
        self.window.set_needs_display()

class Cell(Responder):
    SELECTION_STYLE_INVERT = const(1)
    SELECTION_STYLE_INDICATOR = const(2)
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
    :param indent: Temporary API; indent from the left. Will eventually become a proper inset.
    :param selection_style: Sets the appearance of the cell when it is the active responder.
    """
    def __init__(
        self,
        font,
        *,
        x=0,
        y=0,
        width=0,
        height=0,
        color=0xFFFFFF,
        max_glyphs=None,
        indent=0,
        selection_style=None,
        text="",
    ):
        super().__init__(x=x, y=y, width=width, height=height, max_size=2)
        self.label = Label(font, x=indent, y=self.height // 2, max_glyphs=max_glyphs, color=color, text=text)
        self.selection_style = selection_style
        self.append(self.label)

    def will_become_active(self):
        if self.selection_style is None:
            return
        elif self.selection_style == Cell.SELECTION_STYLE_INVERT:
            bg_bitmap = displayio.Bitmap(self.width, self.height, 1)
            bg_palette = displayio.Palette(1)
            bg_palette[0] = self.label.color
            self.background = displayio.TileGrid(bg_bitmap, pixel_shader=bg_palette, x=0, y=0)
            self.insert(0, self.background)
            self.label.color = ~self.label.color & 0xFFFFFF
        elif self.selection_style == Cell.SELECTION_STYLE_INDICATOR:
            bg_bitmap = displayio.Bitmap(8, self.height, 1)
            bg_palette = displayio.Palette(1)
            bg_palette[0] = self.label.color
            self.background = displayio.TileGrid(bg_bitmap, pixel_shader=bg_palette, x=16, y=0)
            self.append(self.background)
        self.window.set_needs_display()

    def will_resign_active(self):
        if self.selection_style is None:
            return
        if self.background is not None:
            self.remove(self.background)
        if self.selection_style == Cell.SELECTION_STYLE_INVERT:
            self.label.color = ~self.label.color & 0xFFFFFF
        self.window.set_needs_display()

class Table(Responder):
    """A ``Table`` manages a group of ``Cell``s, displaying as many as will fit in the view's display area.
    If there is more than one screen's worth of content, an on-screen previous/next page button can be added
    (for touchscreen interfaces) or the table can respond to previous/next events (button-based interface).
    :param font: The font for the cells.
    :param x: The x position of the view.
    :param y: The y position of the view.
    :param width: The width of the view in pixels.
    :param height: The height of the view in pixels.
    :param color: The foreground color for label text.
    :param indent: Temporary API; cell indent from the left. Will eventually become a proper inset.
    :param cell_height: The height of each row in the table.
    :param selection_style: Sets the appearance of cell that is the active responder.
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
        color=0xFFFFFF,
        indent=0,
        cell_height=32,
        selection_style=None,
        show_navigation_buttons=False,
    ):
        max_cells = height // cell_height
        super().__init__(x=x, y=y, width=width, height=height, max_size=max_cells + (1 if show_navigation_buttons else 0))
        self.cell_height = cell_height
        self.font = font
        self.color = color
        self.indent = indent
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
            cell = Cell(self.font, x=0, y=i * self.cell_height, width=self.width, height=self.cell_height, color=self.color,
            indent=self.indent, selection_style=self.selection_style if self.window.highlight_active_responder else None,
            text=self._items[self._start_offset + i])
            self.add_subview(cell)
        if self._add_buttons:
            for i in range(0, 2):
                cell = Cell(self.font, x=i * self.width // 2, y=self._cells_per_page * self.cell_height, width=self.width // 2, height=self.cell_height,
                color=self.color, selection_style=Cell.SELECTION_STYLE_INVERT if self.window.highlight_active_responder else None,
                text="Previous" if i is 0 else "Next")
                self.add_subview(cell)
        if self[0] is not None:
            self[0].become_active()

    def previous_page(self):
        if self._start_offset > 0:
            self._start_offset -= self._cells_per_page
            self.update_cells()

    def next_page(self):
        if self._start_offset + self._cells_per_page < len(self.items):
            self._start_offset += self._cells_per_page
            self.update_cells()

    def handle_event(self, event):
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
            if event.event_type == Event.BUTTON_UP and cell_index > 0:
                self[cell_index - 1].become_active()
                return True
            elif event.event_type == Event.BUTTON_DOWN and cell_index < len(self) - 1:
                self[cell_index + 1].become_active()
                return True
        return super().handle_event(event)
