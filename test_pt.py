import sys
import asyncio
import selectors

if sys.platform == 'darwin':
    class SelectEventLoop(asyncio.SelectorEventLoop):
        def __init__(self):
            super().__init__(selectors.SelectSelector())
    class SelectEventLoopPolicy(asyncio.DefaultEventLoopPolicy):
        def new_event_loop(self):
            return SelectEventLoop()
    asyncio.set_event_loop_policy(SelectEventLoopPolicy())

from prompt_toolkit import Application
from prompt_toolkit.layout import Layout
from prompt_toolkit.layout.containers import Window
from prompt_toolkit.layout.controls import FormattedTextControl
from prompt_toolkit.key_binding import KeyBindings
from prompt_toolkit.output.defaults import create_output

kb = KeyBindings()
@kb.add("enter")
@kb.add("escape")
def exit_(event):
    event.app.exit()

app = Application(
    layout=Layout(Window(FormattedTextControl("press enter"))),
    key_bindings=kb,
    output=create_output(sys.stderr)
)
print("Starting...", file=sys.stderr)
app.run()
print("Done", file=sys.stderr)
