Source: Arcade 2.6.17 doc/examples/platform_tutorial/step_10.rst



## Step 10 - Multiple Levels and Other Layers

Now that we've seen the basics of loading a Tiled map, we'll give another example with some more
features. In this example we'll add the following things:

* New layers including foreground, background, and "Don't Touch"

  * The background layer will appear behind the player
  * The foreground layer will appear in front of the player
  * The Don't Touch layer will cause the player to be reset to the start

* The player resets to the start if they fall off the map
* If the player gets to the right side of the map, the program attempts to load the next map

  * This is achieved by naming the maps with incrementing numbers, something like "map_01.json",
    "map_02.json", etc. Then having a level attribute to track which number we're on and increasing
    it and re-running the setup function.

To start things off, let's add a few constants at the top of our game. The first one we need to define is the size of
a sprite in pixels.  Along with that we need to know the grid size in pixels.  These are used to calculate
the end of the level.

    :caption: Multiple Levels - Constants
    :lines: 15-16

Next we need to define a starting position for the player, and then since we're starting to have a larger number of
layers in our game, it will be best to store their names in variables in case we need to change them later.

    :caption: Multiple Levels - Constants
    :lines: 23-32

Then in the ``__init__`` function we'll add two new values. One to know where the right
edge of the map is, and one to keep track of what level we're on, and add a new game over sound.

    :caption: Multiple Levels - Init Function
    :lines: 69-78

Also in our ``__init__`` function we'll need a variable to tell us if we need to reset the score.  This will be the case
if the player fails the level.  However, now that the player can pass a level, we need to keep
the score when calling our ``setup`` function for the new level.  Otherwise it will reset
the score back to 0

    :caption: Multiple Levels - Init Function
    :lines: 66-68

Then in our ``setup`` function we'll change up our map name variable to use that new level attribute,
and add some extra layer specific options for the new layers we've added to our map.

    :caption: Multiple Levels - Setup Function
    :lines: 87-101

Now in order to make our player appear behind the "Foreground" layer, we need to add a line in our
``setup`` function before we create the player Sprite. This will basically be telling our Scene where
in the render order we want to place the player. Previously we haven't defined this, and so it's always
just been added to the end of the render order.

    :caption: Multiple Levels - Setup Function
    :lines: 115-127
    :emphasize-lines: 1-6

Next in our ``setup`` function we need to check to see if we need to reset the score or keep it.

    :caption: Multiple Levels - Setup Function
    :lines: 106-113
    :emphasize-lines: 5-8

Lastly in our ``setup`` function we need to calculate the ``end_of_map`` value we added earlier in ``init``.

    :caption: Multiple Levels - Setup Function
    :lines: 131-132

The ``on_draw``, ``on_key_press``, and ``on_key_release`` functions will be unchanged for this section, so the
last thing to do is add a few things to the ``on_update`` function. First we check if the player has fallen off
of the map, and if so, we move them back to the starting position. Then we check if they collided with something
from the "Don't Touch" layer, and if so reset them to the start. Lastly we check if they've reached the end of the
map, and if they have we increment the level value, tell our ``setup`` function not to reset the score, and then re-run
the ``setup`` function.

    :caption: Multiple Levels - Update Function
    :lines: 224-251

  

    What else might you want to do?

    * sprite_enemies_in_platformer
    * sprite_face_left_or_right
    * Bullets (or something you can shoot)

      * sprite_bullets
      * sprite_bullets_aimed
      * sprite_bullets_enemy_aims

    * Add sprite_explosion_bitmapped
    * Add sprite_move_animation

Source Code
~~~~~~~~~~~

    :caption: Multiple Levels
    :linenos:
    :emphasize-lines: 23-32,66-67,69-70,75,84-85,87-98,110-115,120-121,126-127,137,219-224,226-235,237-243