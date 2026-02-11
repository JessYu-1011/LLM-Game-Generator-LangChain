Source: Arcade 2.6.17 doc/examples/gui_flat_button.rst

:orphan:


# Flat Text Buttons

For an introduction the GUI system, see gui_concepts.

The `arcade.gui.UIFlatButton` is a simple button with a text label.
It doesn't have any three-dimensional look to it.

    :width: 600px
    :align: center
    :alt: Screen shot of flat text buttons

There are three ways to process button click events:

1. Create a class with a parent class of `arcade.UIFlatButton`
   and implement a method called `on_click`.
2. Create a button, then set the `on_click` attribute of that button to
   equal the function you want to be called.
3. Create a button. Then use a decorator to specify a method to call
   when an `on_click` event occurs for that button.

This code shows each of the three ways above. Code should pick ONE of the three
ways and standardize on it though-out the program. Do NOT write code
that uses all three ways.


    :caption: gui_flat_button.py
    :linenos:
