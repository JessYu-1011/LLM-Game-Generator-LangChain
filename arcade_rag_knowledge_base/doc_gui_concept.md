Source: Arcade 2.6.17 doc/gui/concept.rst


## GUI Concepts

GUI elements are represented as instances of `UIWidget`. The GUI is structured like a tree, every widget
can have other widgets as children.

The root of the tree is the `UIManager`. The UIManager connects the user interactions with the GUI.
Read more about UIEvent.

Classes of Arcades GUI code are prefixed with UI- to make them easy to identify and search for in autocompletion.

# UIWidget

`UIWidget` are the core of Arcades GUI. A widget represents the behaviour and graphical
representation of any element (like Buttons or Text)

A `UIWidget` has following properties

**rect**
    x and y coordinates (bottom left of the widget), width and height

**children**
    Child widgets, rendered within this widget
    A `UIWidget` will not move or resize its children, use a `UILayout` instead.

**size_hint**
    tuple of two floats, defines how much of the parents space it would like to occupy (range: 0.0-1.0).
    For maximal vertical and horizontal expansion, define `size_hint` of 1 for the axis.

**size_hint_min**
    tuple of two ints, defines minimal size of the widget.
    If set, changing the size of a widget to a lower values will use this size instead.

**size_hint_max**
    tuple of two ints, defines maximum size of the widget.
    If set, changing the size of a widget to a higher values will use this size instead.

    *size_hint*, *size_hint_min*, and *size_hint_max* are values that are additional information of a widget, but do not
    effect the widget on its own. `UILayout` may use these information to place or resize a widget.

Rendering
.........

:meth:`UIWidget.do_render` is called recursively if rendering was requested via :meth:`UIWidget.trigger_render`.
In case widgets have to request their parents to render use :meth:`UIWidget.trigger_full_render`

The widget has to draw itself and child widgets within :meth:`UIWidget.do_render`. Due to the deferred functionality
render does not have to check any dirty variables, as long as state changes use the trigger function.

For widgets, that might have transparent areas, they have to request a full rendering.

    Enforced rendering of the whole GUI might be very expensive!

# UILayout and UIWrapper

`UILayout` are widgets, which reserve the option to move or resize children. They might respect special properties
of a widget like *size_hint*, *size_hint_min*, or *size_hint_max*.

`UIWrapper` are widgets that are used to wrap a single child widget to apply additional effects
like borders or space around.


Algorithm (WIP, not fully implemented)
......................................

`UIManager` triggers the layout and render process right before the actual frame draw.
This opens the possibility, to adjust to multiple changes only ones.

Executed steps within `UIBoxLayout`:

1. :meth:`UIBoxLayout.do_layout`
    1. collect current size, size_hint, size_hint_min/max of children
    2. calculate the new position and sizes
    3. set position and size of children
2. recursive call `do_layout` on child layouts (done after :meth:`UIBoxLayout.do_layout`)


```python

         ┌─────────┐          ┌────────┐                      ┌────────┐
         │UIManager│          │UILayout│                      │children│
         └────┬────┘          └───┬────┘                      └───┬────┘
              │   do_layout()    ┌┴┐                              │
              │─────────────────>│ │                              │
              │                  │ │                              │
              │                  │ │                              │
              │     ╔════════════╪═╪════╤═════════════════════════╪══════════════╗
              │     ║ place children    │                         │              ║
              │     ╟────────────────use size, size_hint, ...     │              ║
              │     ║            │ │ <─────────────────────────────              ║
              │     ║            │ │                              │              ║
              │     ║            │ │       set size and pos       │              ║
              │     ║            │ │ ─────────────────────────────>              ║
              │     ╚════════════╪═╪══════════════════════════════╪══════════════╝
              │                  │ │                              │
              │                  │ │                              │
              │     ╔═══════╤════╪═╪══════════════════════════════╪══════════════╗
              │     ║ LOOP  │  sub layouts                        │              ║
              │     ╟───────┘    │ │                              │              ║
              │     ║            │ │          do_layout()         │              ║
              │     ║            │ │ ─────────────────────────────>              ║
              │     ╚════════════╪═╪══════════════════════════════╪══════════════╝
              │                  └┬┘                              │
              │                   │                               │
              │<─ ─ ─ ─ ─ ─ ─ ─ ─ │                               │
         ┌────┴────┐          ┌───┴────┐                      ┌───┴────┐
         │UIManager│          │UILayout│                      │children│
         └─────────┘          └────────┘                      └────────┘


# UIMixin

Mixin classes are a base class which can be used to apply some specific behaviour. Currently the available Mixins are
still under heavy development.

# Constructs

Constructs are predefined structures of widgets and layouts like a message box or (not yet available) file dialogues.


# Available Elements

- `UIWidget`:
    - `UIFlatButton` - 2D flat button for simple interactions (hover, press, release, click)
    - `UITextureButton` - textured button (use :meth:`arcade.load_texture()`) for simple interactions (hover, press, release, click)
    - `UILabel` - Simple text, supports multiline, fits content
    - `UIInputText` - field to accept user text input
    - `UITextArea` - Multiline scrollable text widget.
    - `UISpriteWidget` - Embeds a Sprite within the GUI tree
- `UILayout`:
    - `UIBoxLayout` - Places widgets next to each other (vertical or horizontal)
- `UIWrapper`:
    - `UIPadding` - Add space around a widget
    - `UIBorder` - Add border around a widget
    - `UIAnchorWidget` - Used to position UIWidgets relative on screen
- Constructs
    - `UIMessageBox` - Popup box with a message text and a few buttons.
- Mixins
    - `UIDraggableMixin` - Makes a widget draggable.
    - `UIMouseFilterMixin` - Catches mouse events that occure within the widget boundaries.
    - `UIWindowLikeMixin` - Combination of `UIDraggableMixin` and `UIMouseFilterMixin`.


# UIEvents

UIEvents are fully typed dataclasses, which provide information about a event effecting the UI.
Events are passed top down to every `UIWidget` by the UIManager.

General pyglet window events are converted by the UIManager into UIEvents and passed via dispatch_event
to the ``on_event`` callbacks.

Widget specific UIEvents like UIOnClick are dispatched via "on_event" and are then  dispatched as specific event types (like 'on_click')

- `UIEvent` - Base class for all events
- `UIMouseEvent` - Base class for mouse related event
    - `UIMouseMovementEvent` - Mouse moves
    - `UIMousePressEvent` - Mouse button pressed
    - `UIMouseDragEvent` - Mouse pressed and moved (drag)
    - `UIMouseReleaseEvent` - Mouse button released
    - `UIMouseScrollEvent` - Mouse scolls
- `UITextEvent` - Text input from user
- `UITextMotionEvent` - Text motion events like arrows
- `UITextMotionSelectEvent` - Text motion events for selection
- `UIOnClickEvent` - Click event of `UIInteractiveWidget` class
- `UIOnChangeEvent` - A value of a `UIWidget` has changed
- `UIOnUpdateEvent` - arcade.Window `on_update` callback

# Different Event Systems

The GUI uses different event systems, dependent on the required flow. A game developer should mostly interact with UIEvents
which are dispatched from specific UIWidgets like ``on_click`` of a button.

In rare cases a developer might implement some UIWidgets or wants to modify the existing GUI behavior. In those cases a
developer might register own Pyglet event types on UIWidgets or overwrite the ``UIWidget.on_event`` method.

### Pyglet Window Events

Received by UIManager, dispatched via ``UIWidget.dispatch_event("on_event", UIEvent(...))``.
Window Events are wrapped into subclasses of UIEvent.

### Pyglet EventDispatcher - UIWidget

UIWidgets implement Pyglets EventDispatcher and register an ``on_event`` event type.
``UIWidget.on_event`` contains specific event handling and should not be overwritten without deeper understanding of the consequences.
To add custom event handling use the decorator syntax to add another listener (``@UIWidget.event("on_event")``).

### UIEvents

UIEvents are typed representations of events that are passed within the GUI. UIWidgets might define their own UIEvents.

### _Property

``_Property`` is an internal, experimental, pure-Python implementation of Kivy Properties. They are used to detect attribute
changes of UIWidgets and trigger rendering. They should only be used in arcade internal code.

