import displayio
from adafruit_display_text.label import Label
from adafruit_display_shapes.roundrect import RoundRect
from adafruit_display_shapes.rect import Rect
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

    def generate_event(self, event_type, user_info={}):
        """Generates an event. Tasks can call this method to create events from external inputs; for example, if the user pressed the
        "Select" button, you could generate a BUTTON_SELECT event in your button task. The window's active responder gets first crack
        at handling the event. If the active responder cannot handle the event, it will bubble up the responder chain.
        :param event_type: The type of event to generate.
        :param user_info: An optional dictionary with additional information about the event."""
        self.window.active_responder.handle_event(Event(event_type, user_info))

class Style():
    """An object describing the physical appearance of a Responder. Technically all params are optional (default values are substituted),
    but if the style is applied to any object with a text label, the ``font`` property must be supplied.
    :param font: The font to use for any text labels.
    :param foreground_color: The color for any text or control outlines.
    :param background_color: The color for any fills or backgrounds.
    :param active_foreground_color: The color for any text or control outlines when the responder is active.
    :param active_background_color: The color for any fills or backgrounds when the responder is active.
    :param button_radius: The corner radius for buttons and similar tappable controls.
    :param container_radius: The corner radius for containers like modal dialogs or popup menus.
    :param content_insets: a 4-tuple of insets from the top, right, bottom and left. Not all controls use this.
    """
    def __init__(
        self,
        *,
        font=None,
        foreground_color=0xFFFFFF,
        background_color=0x000000,
        active_foreground_color=0x000000,
        active_background_color=0xFFFFFF,
        button_radius=10,
        container_radius=5,
        content_insets=(0, 0, 0, 0),
    ):
        self.font = font
        self.foreground_color = foreground_color
        self.background_color = background_color
        self.active_foreground_color = active_foreground_color
        self.active_background_color = active_background_color
        self.button_radius = button_radius
        self.container_radius = container_radius
        self.content_insets = content_insets

class Responder(displayio.Group):
    """Base class for ``circuitpyui`` classes. Has a position and a size.
    When you add a responder to another responder using ``add_subview``, it will join a chain of responders that can handle
    and pass along ``Event``s. When an event is generated, the originating responder will have a chance to handle it.
    If it does not, the event should pass to the next_responder.
    :param x: The x position of the view.
    :param y: The y position of the view.
    :param width: The width of the view in pixels.
    :param height: The height of the view in pixels.
    :param style: Optional Style object. If no style is specified, we'll fall back to the style of the window.
    :param max_size: Maximum number of groups and responders that will be added.
    """
    def __init__(
        self,
        *,
        x=0,
        y=0,
        width=0,
        height=0,
        style=None,
        max_size=5,
    ):
        super().__init__(x=x, y=y, max_size=max_size)
        self.x = x
        self.y = y
        self.width = width
        self.height = height
        self._style = style
        self.next_responder = None
        self.window = None
        self.actions = None

    @property 
    def style(self):
        if self._style is not None:
            return self._style
        elif self.window is not None:
            return self.window._style
        return None

    def add_subview(self, view):
        """Adds a Responder to the view hierarchy. Only for ``Responder``s and their subclasses;
        if you are adding a plain displayio ``Group``, use append() instead.
        :param view: The view to add to the hierarchy."""
        view.next_responder = self
        view.window = self if self.__class__ is Window else self.window
        self.append(view)
        if view.window is not None:
            view.window.set_needs_display()
        view.moved_to_window()

    def remove_subview(self, view):
        """Removes a Responder from the view hierarchy. Only for ``Responder``s and their subclasses;
        if you are removing a plain displayio ``Group``, use remove() instead.
        :param view: The view to remove from the hierarchy."""
        if view == view.window.active_responder:
            view.resign_active()
        view.next_responder = None
        view.window = None
        self.remove(view)
        if self.window is not None:
            self.window.set_needs_display()

    def become_active(self):
        """Causes this view to become the active responder in the window."""
        old_responder = self.window.active_responder
        old_responder.will_resign_active()
        self.window.active_responder = None
        old_responder.did_resign_active()
        self.will_become_active()
        self.window.active_responder = self
        self.did_become_active()

    def resign_active(self):
        """Causes this view to become the active responder in the window."""
        if self is not self.window.active_responder:
            return
        self.will_resign_active()
        self.window.active_responder = None
        self.did_resign_active()
        self.window.will_become_active()
        self.window.active_responder = self.window
        self.window.did_become_active()

    def moved_to_window(self):
        """Called when the view moves to its window. Useful for setting up any styled objects, since you now
        have access to both the view's style and the window's style."""
        pass

    def will_become_active(self):
        """Called before a view becomes the active responder. Subclasses can override this method to configure
        their appearance in response to this event; they are guaranteed to become active in just a moment.
        Note that the window's active_responder will be None when this method is called."""
        pass

    def did_become_active(self):
        """Called after a view becomes the active responder. Subclasses can override this method to perform
        any required post-activation tasks.
        """
        pass

    def will_resign_active(self):
        """Called before a view resigns its status as the active responder. Subclasses can override this method
        to configure their appearance in response to this event; they are guaranteed to become inactive shortly.
        """
        pass

    def did_resign_active(self):
        """Called after a view resigns its status as the active responder. Subclasses can override this to perform
        any cleanup tasks. Note that the window's active_responder will be None when this method is called."""
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
            return True
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

    def __hash__(self):
        """Needed to store the view in the focus target dict. Not sure if this is wise; curretly str(group) returns a string like
        <Button object at 200063d0> which works, but it feels fragile. Open to a better way of doing this."""
        return hash(str(self))

class Window(Responder):
    """A window is the topmost view in a chain of responders. All responders should live in a tree under the window.
    In a touch environment, the window defers to Responder's ``handle_touch`` method to forward a touch to the correct responder.
    In a cursor-based environment, the window can handle pushbutton events to move focus between responders.
    :param style: Style object defining the appearance of views in this window. Required, and recommend setting a font.
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
        style,
        *,
        x=0,
        y=0,
        width=0,
        height=0,
        max_size=5,
        highlight_active_responder=True,
    ):
        super().__init__(x=x, y=y, width=width, height=height, style=style, max_size=max_size)
        self.x = x
        self.y = y
        self.width = width
        self.height = height
        self.highlight_active_responder=highlight_active_responder
        self.next_responder = None
        self.active_responder = self
        self.event_queue = []
        self.dirty = False
        self.focus_info = None

    def handle_event(self, event):
        """Override of ``Responder``'s ``handle_event``. If you have provided focus targets, the ``Window`` will consume directional
        button presses and move the active responder if possible. Note that subviews can also consume these button presses and prevent
        the window from moving focus (useful for, say, a slider that wants to steal left and right presses, but still pass along
        up and down presses).
        :param event: the event to be handled.
        """
        if self.focus_info is None or not event.event_type in [Event.BUTTON_UP, Event.BUTTON_RIGHT, Event.BUTTON_DOWN, Event.BUTTON_LEFT] or not self.active_responder in self.focus_info:
            return super().handle_event(event)

        if event.event_type is Event.BUTTON_UP:
            target = self.focus_info[self.active_responder][0]
        if event.event_type is Event.BUTTON_RIGHT:
            target = self.focus_info[self.active_responder][1]
        if event.event_type is Event.BUTTON_DOWN:
            target = self.focus_info[self.active_responder][2]
        if event.event_type is Event.BUTTON_LEFT:
            target = self.focus_info[self.active_responder][3]
        if target is not None:
            target.become_active()
            return True
        return super().handle_event(event)

    def set_focus_targets(self, view, *, up=None, right=None, down=None, left=None):
        """Tells the window which view should receive focus for a given directional button press.
        :param view: The view whose focus targets you are setting.
        :param up: The view that should be selected when a BUTTON_UP event is handled, or None if focus should stay on this view.
        :param right: The view that should be selected when a BUTTON_RIGHT event is handled, or None if focus should stay on this view.
        :param down: The view that should be selected when a BUTTON_DOWN event is handled, or None if focus should stay on this view.
        :param left: The view that should be selected when a BUTTON_LEFT event is handled, or None if focus should stay on this view.
        """
        if self.focus_info is None:
            self.focus_info = {}
        self.focus_info[view] = (up, right, down, left)

    def queue_event(self, responder, event):
        """Queues an event to be handled after the current run loop task completes. This is useful to avoid exhausting the stack;
        for example, after recursively locating the source of a touch event, we can queue the tap event so that the user's action
        doesn't get called from the bottom of that stack of calls.
        :param responder: the responder that should take first crack at handling the event.
        :param event: the event to give it."""
        self.event_queue.append((responder, event))

    def needs_display(self):
        """Checks whether the window needs display. Only really useful for that require manual refresh (like e-paper displays)."""
        return self.dirty

    def set_needs_display(self, needs_display = True):
        """Sets or resets the value that will be returned from ``needs_display``. Automatically set whenever add_ or remove_subview
        is called; if you add any raw displayio Groups or change things like label text, you may need to set this manually. And then
        call ``set_needs_display(False)`` once you do refresh your display."""
        self.dirty = needs_display

class Button(Responder):
    """a Responder that draws an outline and shows either an image or a text label.
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
        super().__init__(x=x, y=y, width=width, height=height, style=style, max_size=2)
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
    SELECTION_STYLE_HIGHLIGHT = const(1)
    SELECTION_STYLE_INDICATOR = const(2)
    """A ``Cell`` is a specialized responder intended for use with a table or grid view. Comes with one label.
    You should not add additional groups to a cell; it has a max_size of 1. Eventually hope to add additional
    styles that support more labels or accessory views.
    :note: at this time a background is only drawn on the active row; other rows respect style.foreground_color,
           but style.background_color is ignored.
    :param font: The font for the label.
    :param x: The x position of the view.
    :param y: The y position of the view.
    :param width: The width of the view in pixels.
    :param height: The height of the view in pixels.
    :param style: a Style object defining the Cell's appearance, or None to fall back to the Cell's appearance.
    :param max_glyphs: Maximum number of glyphs in the label. Optional if ``text`` is provided.
    :param text: Text for the label.
    :param selection_style: Sets the appearance of the cell when it is the active responder.
    """
    def __init__(
        self,
        *,
        x=0,
        y=0,
        width=0,
        height=0,
        style=None,
        max_glyphs=None,
        selection_style=None,
        text="",
    ):
        super().__init__(x=x, y=y, width=width, height=height, style=style, max_size=2)
        self.text = text
        self.selection_style = selection_style

    def moved_to_window(self):
        self.label = Label(self.style.font, x=self.style.content_insets[3], y=self.height // 2, max_glyphs=len(self.text), color=self.style.foreground_color, text=self.text)
        if self.selection_style == Cell.SELECTION_STYLE_HIGHLIGHT:
            # quick hack, center previous/next buttons
            # TODO: add alignment to the Style class
            dims = self.label.bounding_box
            self.label.x = (self.width - dims[2]) // 2
            self.label.y = self.height // 2
        self.selection_style = self.selection_style
        self.append(self.label)

    def will_become_active(self):
        if self.selection_style is None:
            return
        elif self.selection_style == Cell.SELECTION_STYLE_HIGHLIGHT:
            self.background = Rect(0, 0, self.width, self.height, fill=self.style.active_background_color, outline=self.style.active_background_color)
            self.insert(0, self.background)
            self.label.color = self.style.active_foreground_color
        elif self.selection_style == Cell.SELECTION_STYLE_INDICATOR:
            self.background = Rect(16, 0, 8, self.height, fill=self.style.active_background_color, outline=self.style.active_background_color)
            self.append(self.background)
        self.window.set_needs_display()

    def will_resign_active(self):
        if self.selection_style is None:
            return
        if self.background is not None:
            self.remove(self.background)
        if self.selection_style == Cell.SELECTION_STYLE_HIGHLIGHT:
            self.label.color = self.style.foreground_color
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
    :param style: a Style object defining the Table's appearance, or None to fall back to the Window's appearance.
    :param indent: Temporary API; cell indent from the left. Will eventually become a proper inset.
    :param cell_height: The height of each row in the table.
    :param selection_style: Sets the appearance of cell that is the active responder.
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
        selection_style=None,
        show_navigation_buttons=False,
    ):
        max_cells = height // cell_height
        super().__init__(x=x, y=y, width=width, height=height, style=style, max_size=max_cells + (1 if show_navigation_buttons else 0))
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
                selection_style=Cell.SELECTION_STYLE_HIGHLIGHT if self.window.highlight_active_responder else None, text="Previous" if i is 0 else "Next")
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

class Alert(Responder):
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
        super().__init__(x=0, y=0, width=0, height=0, style=style, max_size=2 + len(button_text))
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

    def did_become_active(self):
        if len(self.buttons):
            self.buttons[0].become_active()

    def handle_event(self, event):
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
