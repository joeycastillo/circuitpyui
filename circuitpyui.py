import displayio
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
    :param next_responder: The responder responsible for handling events that this responder does not.
    """
    def __init__(
        self,
        *,
        x=0,
        y=0,
        width=0,
        height=0,
        max_size=5,
        next_responder=None
    ):
        super().__init__(x=x, y=y, max_size=max_size)
        self.x = x
        self.y = y
        self.width = width
        self.height = height
        self.next_responder = next_responder

    def contains(self, point):
        """Used to determine if a point is contained within this responder, mostly for touch UI.
        :param point: a tuple with the x and y value.
        :return: True if the point was inside this view, False if not."""
        return (self.x <= point[0] <= self.x + self.width) and (self.y <= point[1] <= self.y + self.height)

    def handle_event(self, event):
        """Subclasses should override this to handle Events that are relevant to them.
        :param event: an Event class with a required event_type and an optional user_info dictionary.
        :return: True if the event was handled, False if not."""
        if self.next_responder is not None:
            return self.next_responder.handle_event(event)
        return False

    def handle_touches(self, touched, touches):
        """When using a touch UI, call this method repeatedly to handle any touch events coming in.
        Subclasses should not need to override this method.
        :param touched: a boolean indicating whether there is a finger on the display.
        :param touches: a list of touches. Each should have an x and y value.
        :return: the topmost view that was touched, or None if the touch fell outside of any view."""
        if not touched or not touches:
            return None # eventually maybe use this to inform touch up events?
        touch = (touches[0]["x"], touches[0]["y"])
        if not self.contains(touch):
            return None
        for subview in reversed(self): # process frontmost layers first
            try:
                retval = subview.handle_touches(touched, touches)
                if retval is not None:
                    return retval
            except AttributeError:
                continue # plain displayio groups can live in the view hierarchy, but they don't participate in responder chains.
        if self.contains(touch):
            self.handle_event(Event(Event.TOUCH_BEGAN, touch))
            return self
        return None

class Window(Responder):
    """A window is the topmost view in a chain of responders. All responders should live in a tree under the window.
    In a touch environment, the window defers to Responder's ``handle_touches`` method to forward a touch to the correct responder.
    In a cursor-based environment, the window can handle pushbutton events to move focus between responders.
    :param x: The x position of the view.
    :param y: The y position of the view.
    :param width: The width of the view in pixels.
    :param height: The height of the view in pixels.
    :param max_size: Maximum number of groups that will be added.
    :param next_responder: The responder responsible for handling events that this responder does not.
    """
    def __init__(
        self,
        *,
        x=0,
        y=0,
        width=0,
        height=0,
        max_size=5,
        next_responder=None
    ):
        super().__init__(x=x, y=y, width=width, height=height, max_size=max_size, next_responder=next_responder)
        self.x = x
        self.y = y
        self.width = width
        self.height = height
        self.next_responder = next_responder
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
        next_responder=None,
        label=None,
        font=None
    ):
        super().__init__(x=x, y=y, width=width, height=height, max_size=max_size, next_responder=next_responder)
        self.x = x
        self.y = y
        self.width = width
        self.height = height
        self.next_responder = next_responder
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
