import displayio
from micropython import const

class Event():
    TAPPED = const(1)
    TOUCH_BEGAN = const(10)
    BUTTON_LEFT = const(100)
    BUTTON_DOWN = const(101)
    BUTTON_UP = const(102)
    BUTTON_RIGHT = const(103)
    BUTTON_A = const(104)
    BUTTON_B = const(105)
    BUTTON_SELECT = const(106)
    BUTTON_START = const(107)
    # aliases for Open Book buttons
    BUTTON_CENTER = BUTTON_A
    BUTTON_PREV = BUTTON_SELECT
    BUTTON_NEXT = BUTTON_START
    BUTTON_LOCK = BUTTON_B

    def __init__(self, event_type, user_info):
        self.event_type = event_type
        self.user_info = user_info

class Task():
    """a ``Task`` is a simple class with one method, ``run``. ``Task``s are a way for a circuitpyui application to accept
    input from (and send output to) the hardware around it. For example, you might create a ``TouchscreenTask`` that routes
    touches from a touchscreen to an application's window, or a ``ButtonTask`` that converts button presses to ``Event``s
    that ``Responders`` can consume and respond to.
    You should create ``Task``s  for any event sources and output peripherals associated with your hardware. Ideally they
    should be decoupled from application logic, merely generating events or (in the case of touchscreens) passing touches.
    Your ``run`` method should not return anything; the ``Application`` will leave its run loop if any ``Task``'s ``run``
    method returns True or anything truthy."""
    def __init__(self):
        pass

    def run(self, application):
        pass

class Application():
    """an ``Application`` manages a set of ``Task``s running in a loop, as well as a ``Window`` that displays your UI.
    You should subclass ``Application`` and encapsulate all your program-specific logic within that custom class.
    This is also where you will add handlers for ``Event``s: use the ``View``'s ``add_action`` method, and pass
    in an instance method with a signature like ``handler(self, event)``. When the ``View`` gets a matching
    ``Event``, your handler will be called."""
    def __init__(self, window):
        self.window = window
        self.window.application = self
        self.tasks = []

    def add_task(self, task):
        """Adds a task to the run loop. Tasks run in the order added, so it probably makes sense to add your input tasks
        (i.e. collect touches and button presses) before your output tasks (refresh the screen, etc).
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
                    (view, event) = self.window.event_queue.pop(0)
                    view.handle_event(event)

    def generate_event(self, event_type, user_info={}):
        """Generates an event. Tasks can call this method to create events from external inputs; for example, if the user pressed the
        "Left" button, you could generate a BUTTON_LEFT event in your button task. The window's active view gets first crack
        at handling the event. If the active view cannot handle the event, it will bubble up the responder chain.
        :param event_type: The type of event to generate.
        :param user_info: An optional dictionary with additional information about the event."""
        self.window.active_responder.handle_event(Event(event_type, user_info))

class Style():
    """An object describing the physical appearance of a View. Technically all params are optional (default values are substituted),
    but if the style is applied to any object with a text label, the ``font`` property must be supplied.
    :param font: The font to use for any text labels.
    :param foreground_color: The color for any text or control outlines.
    :param background_color: The color for any fills or backgrounds.
    :param active_foreground_color: The color for any text or control outlines when the view is active.
    :param active_background_color: The color for any fills or backgrounds when the view is active.
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

class View(displayio.Group):
    """Base class for ``circuitpyui`` classes. Has a position and a size.
    When you add a view to another view using ``add_subview``, it will join a chain of responders that can handle
    and pass along ``Event``s. When an event is generated, the originating view will have a chance to handle it.
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
        """Adds a View to the view hierarchy. Only for ``View``s and their subclasses;
        if you are adding a plain displayio ``Group``, use append() instead.
        :param view: The view to add to the hierarchy."""
        view.next_responder = self
        view.window = self if self.__class__ is Window else self.window
        self.append(view)
        if view.window is not None:
            view.window.set_needs_display()
        view.moved_to_window()

    def remove_subview(self, view):
        """Removes a View from the view hierarchy. Only for ``View``s and their subclasses;
        if you are removing a plain displayio ``Group``, use remove() instead.
        :param view: The view to remove from the hierarchy."""
        if view == view.window.active_responder:
            view.resign_active()
        view.next_responder = None
        view.window = None
        self.remove(view)
        if self.window is not None:
            self.window.set_needs_display()

    def become_active(self, event=None):
        """Causes this view to become the active view in the window.
        :param event: Very optional. Contains an event if the change in state was in response to an event."""
        old_responder = self.window.active_responder
        old_responder.will_resign_active(event)
        self.window.active_responder = None
        old_responder.did_resign_active(event)
        self.will_become_active(event)
        self.window.active_responder = self
        self.did_become_active(event)

    def resign_active(self, event=None):
        """Causes this view to become the active view in the window."""
        if self is not self.window.active_responder:
            return
        self.will_resign_active(event)
        self.window.active_responder = None
        self.did_resign_active(event)
        self.window.will_become_active(event)
        self.window.active_responder = self.window
        self.window.did_become_active(event)

    def moved_to_window(self):
        """Called when the view moves to its window. Useful for setting up any styled objects, since you now
        have access to both the view's style and the window's style."""
        pass

    def will_become_active(self, event=None):
        """Called before a view becomes the active view. Subclasses can override this method to configure
        their appearance in response to this event; they are guaranteed to become active in just a moment.
        Note that the window's active_responder will be None when this method is called.
        :param event: Contains an event if the change in state was in response to an event; otherwise None."""
        pass

    def did_become_active(self, event=None):
        """Called after a view becomes the active view. Subclasses can override this method to perform
        any required post-activation tasks.
        :param event: Contains an event if the change in state was in response to an event; otherwise None."""
        pass

    def will_resign_active(self, event=None):
        """Called before a view resigns its status as the active view. Subclasses can override this method
        to configure their appearance in response to this event; they are guaranteed to become inactive shortly.
        :param event: Contains an event if the change in state was in response to an event; otherwise None."""
        pass

    def did_resign_active(self, event=None):
        """Called after a view resigns its status as the active view. Subclasses can override this to perform
        any cleanup tasks. Note that the window's active_responder will be None when this method is called.
        :param event: Contains an event if the change in state was in response to an event; otherwise None."""
        pass

    def _contains(self, x, y):
        """Internal method to to determine if a point is contained within this view, mostly for touch UI.
        :param x: the x value to test.
        :param y: the y value to test.
        :return: True if the point was inside this view, False if not."""
        return (self.x <= x <= self.x + self.width) and (self.y <= y <= self.y + self.height)

    def handle_event(self, event):
        """Subclasses should override this to handle Events that are relevant to them.
        :param event: an Event class with a required event_type and an optional user_info dictionary.
        :return: True if the event was handled, False if not."""
        window = self if self.__class__ is Window else self.window
        if event.event_type == Event.TOUCH_BEGAN or event.event_type is Event.BUTTON_A:
            self.handle_event(Event(Event.TAPPED, {"originator" : self}))
            return True
        if self.actions is not None and event.event_type in self.actions:
            self.actions[event.event_type](window.application, event)
            return True
        elif self.next_responder is not None:
            return self.next_responder.handle_event(event)
        return False

    def handle_touch(self, touched, x, y):
        """When using a touch UI, call this method repeatedly to handle any touch events coming in.
        If the user touched a view, it will emit a TOUCH_BEGAN event that can propagate through the responder chain.
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
            window = self if self.__class__ is Window else self.window
            window.queue_event(self, Event(Event.TOUCH_BEGAN, {"x": x, "y": y, "originator" : self}))
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

class Window(View):
    """A window is the topmost view in a chain of responders. All responders should live in a tree under the window.
    In a touch environment, the window defers to View's ``handle_touch`` method to forward a touch to the correct view.
    In a cursor-based environment, the window can handle pushbutton events to move focus between responders.
    :param style: Style object defining the appearance of views in this window. Required, and recommend setting a font.
    :param x: The x position of the view.
    :param y: The y position of the view.
    :param width: The width of the view in pixels.
    :param height: The height of the view in pixels.
    :param max_size: Maximum number of groups that will be added.
    :param highlight_active_responder: True to display a selection indicator on the active view, useful for cursor-based
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
        self.application = None
        self.dirty = False
        self.focus_info = None

    def handle_event(self, event):
        """Override of ``View``'s ``handle_event``. If you have provided focus targets, the ``Window`` will consume directional
        button presses and move the active view if possible. Note that subviews can also consume these button presses and prevent
        the window from moving focus (useful for, say, a slider that wants to steal left and right presses, but still pass along
        up and down presses).
        :param event: the event to be handled.
        """
        if self.focus_info is None or not event.event_type in [Event.BUTTON_UP, Event.BUTTON_RIGHT, Event.BUTTON_DOWN, Event.BUTTON_LEFT]:
            return super().handle_event(event)

        focus_source = self.active_responder
        while focus_source is not None and not focus_source in self.focus_info:
            focus_source = focus_source.next_responder
        if focus_source is None:
            return super().handle_event(event)

        if event.event_type is Event.BUTTON_UP:
            focus_target = self.focus_info[focus_source][0]
        if event.event_type is Event.BUTTON_RIGHT:
            focus_target = self.focus_info[focus_source][1]
        if event.event_type is Event.BUTTON_DOWN:
            focus_target = self.focus_info[focus_source][2]
        if event.event_type is Event.BUTTON_LEFT:
            focus_target = self.focus_info[focus_source][3]

        if focus_target is None:
            return super().handle_event(event)
        focus_target.become_active(event)
        return True

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

    def queue_event(self, view, event):
        """Queues an event to be handled after the current run loop task completes. This is useful to avoid exhausting the stack;
        for example, after recursively locating the source of a touch event, we can queue the tap event so that the user's action
        doesn't get called from the bottom of that stack of calls.
        :param view: the view that should take first crack at handling the event.
        :param event: the event to give it."""
        self.event_queue.append((view, event))

    def needs_display(self):
        """Checks whether the window needs display. Only really useful for that require manual refresh (like e-paper displays)."""
        return self.dirty

    def set_needs_display(self, needs_display = True):
        """Sets or resets the value that will be returned from ``needs_display``. Automatically set whenever add_ or remove_subview
        is called; if you add any raw displayio Groups or change things like label text, you may need to set this manually. And then
        call ``set_needs_display(False)`` once you do refresh your display."""
        self.dirty = needs_display
