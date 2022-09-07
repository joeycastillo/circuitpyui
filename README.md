# circuitpyui

A simple displayio-based GUI framework for CircuitPython with minimal dependencies (just `adafruit_display_text` and `adafruit_display_shapes`). Currently targeting Cortex M4 class boards; this will not run on, say, a Feather M0 (not enough RAM).

PLEASE NOTE: this is pre-pre-pre-alpha software; there are probably still bugs and the API for some stuff will likely change. please don't use this for anything really important.

## What is it?

It's an event-driven GUI framework that aims to support either devices with a screen and a D-pad, or a touchscreen. To use it, you define all of your program-specific logic in a subclass of `circuitpyui.Application`. You can define UI elements, attach actions for events, and add input sources that will generate events from the given hardware.

```
class MyApp(circuitpyui.Application):
    def __init__(self, window):
        super().__init__(window)
        self.led = digitalio.DigitalInOut(board.D13)
        self.led.direction = digitalio.Direction.OUTPUT
        button = circuitpyui.Button(x=16, y=16, width=100, height=44, text="Toggle LED")
        button.set_action(MyApp.toggle_led, circuitpyui.Event.TAPPED)
        self.window.add_subview(button)
        button.become_active()
        self.add_task(PyGamerInput())

    def toggle_led(self, event):
        self.led.value = not self.led.value
        time.sleep(0.5)
```

From there, all you have to do is instantiate your Application, hand it a Style and a Window, put it on screen and run it!

```
style = circuitpyui.Style(font=font)
window = circuitpyui.Window(x=0, y=0, width=display.width, height=display.height, style=style)
app = MyApp(window)
display.show(window)

app.run()
```

## Tasks

The `PyGamerInput` class above is from a set of common tasks included with circuitpyui; there are also a couple of touchscreen input tasks, and more will come. These tasks take input like button presses and touchscreen taps and fire off Events in response. The event originates with either the tapped view or, in the case of focus-based UI, the active view when a selection button was pressed (currently button A on Arcada boards).

You can also define your own tasks, and they don't have to be limited to input. For example, the Open Book board has an e-paper display that does not update automatically when UI elements change. For that board, I'm defining a `ScreenRefreshTask` that triggers a manual update when appropriate.

## Events, Actions and the Responder Chain

If you attach an action to a view and that view gets a matching event, your handler will get called and that will be that.

But! If the originating view does not handle the action, that action will "bubble up" through a responder chain. Let's say you have a Window. You add a View to that Window, and three Buttons to that View. The user taps the first button. At this point a TAPPED event is generated, originating from that button. If the Button has no action for a TAPPED event, it won't vanish. Instead, the containing View will have a chance to handle it. If the View also has no action for a TAPPED event, the event will bubble up to the Window, which will have the last chance to handle the event.

This allows for flexibility: if the buttons have very similar functionality (i.e. set color to red, green or blue) you can implement one action on the View, check what button was pressed, and run your common logic with the knowledge of which button triggered the event. Whereas if the buttons have very different functions (radio / air conditioner / ejector seat), you can implement separate actions for each.

For some events that might require an application-wide response (i.e. new sensor data, a timer tick), you can implement the handler on the Window, and it will catch all Events that weren't handled by views lower in the responder chain.

## Contributing

This is very early days, and I'm open to suggestions or pull requests that fix bugs or add useful functionality. A few areas of interest:

* The `adafruit_display_text` label behaves differently from our views in that it centers its content vertically. It might make sense to implement a label in this library that matches the way other views work (from top-left, with a defined width and height)
* more encapsulation of internal class members; for example, Button should have a set_text method instead of expecting the user to edit the Label's text directly.
* Currently the focus system requires manually setting focus targets for each element on screen. It would be great to do this automatically.
* Only a barebones set of Events exist at this time. What other kinds of events do we want to send through the responder chain?
* the Table class was the first thing I put together and may need some refactoring. I also want to add cell styles with multiple labels.
* the Style system is currently a bit barebones; should we have more colors for window backgrounds vs button backgrounds, set outline colors separately? Multiple fonts for bold or italic text?
