Source: Arcade 2.6.17 doc/get_started.rst


# Get Started Here

    :width: 40%
    :class: right-image

## Installation
Arcade can be installed like any other Python
Package. Arcade needs support for OpenGL 3.3+. It does not run on Raspberry
Pi or Wayland.
If you are familiar with Python package management you can just
"pip install" Arcade.
For more detailed instructions see installation-instructions.

## Starting Tutorials

If you are already familiar with basic Python programming, follow the
platformer_tutorial or
`Real Python article <https://realpython.com/arcade-python-game-framework/>`_.
If you are just learning how to program, see
the `Learn Arcade book <https://learn.arcade.academy>`_.


## Arcade Skill Tree

    :width: 40%
    :class: right-image

* Basic Drawing Commands -
  See `How to Draw with Your Computer <https://learn.arcade.academy/en/latest/chapters/05_drawing/drawing.html>`_,
  drawing_primitives

  * ShapeElementLists - Batch together thousands
    of drawing commands into one using a
    `arcade.ShapeElementList`. See examples in
    shape-element-lists.

* Sprites - Almost everything in Arcade is done with the `arcade.Sprite` class.

  * `Basic Sprites and Collisions <https://learn.arcade.academy/en/latest/chapters/21_sprites_and_collisions/sprites.html#basic-sprites-and-collisions>`_
  * `Individually place sprites <https://learn.arcade.academy/en/latest/chapters/25_sprites_and_walls/sprites_and_walls.html#individually-placing-walls>`_
  * `Place sprites with a loop <https://learn.arcade.academy/en/latest/chapters/25_sprites_and_walls/sprites_and_walls.html#placing-walls-with-a-loop>`_
  * `Place sprites with a list <https://learn.arcade.academy/en/latest/chapters/25_sprites_and_walls/sprites_and_walls.html#placing-walls-with-a-list>`_

* Moving player sprites

  * Mouse - sprite_collect_coins
  * Keyboard - sprite_move_keyboard

    * Keyboard, slightly more complex but handles multiple key presses better:
      sprite_move_keyboard_better
    * Keyboard with acceleration, de-acceleration: sprite_move_keyboard_accel
    * Keyboard, rotate and move forward/back like a space ship: sprite_move_angle
  * Game Controller - sprite_move_joystick

    * Game controller buttons - *Supported, but documentation needed.*

* Sprite collision detection

  * Basic detection -
    `Learn arcade book on collisions <https://learn.arcade.academy/en/latest/chapters/21_sprites_and_collisions/sprites.html#the-update-method>`_,
    sprite_collect_coins
  * Understanding collision detection and spatial hashing: collision_detection_performance
  * Sprite Hit boxes

    * Detail amount - `arcade.Sprite`
    * Changing -`arcade.Sprite.hit_box`
    * Drawing - `arcade.Sprite.draw_hit_box`

  * Avoid placing items on walls - sprite_no_coins_on_walls
  * Sprite drag-and-drop - See the solitaire_tutorial.


* Drawing sprites in layers
* Sprite animation

  * Change texture on sprite when hit - sprite_change_coins

* Moving non-player sprites

  * Bouncing - sprite_bouncing_coins
  * Moving towards player - sprite_follow_simple
  * Moving towards player, but with a delay - sprite_follow_simple_2
  * Space-invaders style - slime_invaders
  * Can a sprite see the player? - line_of_sight
  * A-star pathfinding - astar_pathfinding

* Shooting

  * Player shoots straight up - sprite_bullets
  * Enemy shoots every *x* frames - sprite_bullets_periodic
  * Enemy randomly shoots *x* frames - sprite_bullets_random
  * Player aims - sprite_bullets_aimed
  * Enemy aims - sprite_bullets_enemy_aims

* Physics Engines

  * SimplePhysicsEngine - Platformer tutorial platformer_part_three,
    Learn Arcade Book `Simple Physics Engine <https://learn.arcade.academy/en/latest/chapters/25_sprites_and_walls/sprites_and_walls.html#physics-engine>`_,
    Example sprite_move_walls
  * PlatformerPhysicsEngine - From the platformer tutorial: platformer_part_four,

    * sprite_moving_platforms
    * Ladders - Platformer tutorial platformer_part_ten

  * Using the physics engine on multiple sprites - *Supported, but documentation needed.*
  * Pymunk top-down - *Supported, needs docs*
  * Pymunk physics engine for a platformer - pymunk_platformer_tutorial

* View management

  * Minimal example of using views - view_screens_minimal
  * Using views to add a pause screen - view_pause_screen
  * Using views to add an instruction and game over screen - view_instructions_and_game_over

* Window management

  * Scrolling - sprite_move_scrolling
  * Add full screen support - full_screen_example
  * Allow user to resize the window - resizable_window

* Map Creation

  * Programmatic creation

    * `Individually place sprites <https://learn.arcade.academy/en/latest/chapters/25_sprites_and_walls/sprites_and_walls.html#individually-placing-walls>`_
    * `Place sprites with a loop <https://learn.arcade.academy/en/latest/chapters/25_sprites_and_walls/sprites_and_walls.html#placing-walls-with-a-loop>`_
    * `Place sprites with a list <https://learn.arcade.academy/en/latest/chapters/25_sprites_and_walls/sprites_and_walls.html#placing-walls-with-a-list>`_

  * Procedural Generation

    * maze_depth_first
    * maze_recursive
    * procedural_caves_bsp
    * procedural_caves_cellular

  * TMX map creation - Platformer tutorial: platformer_part_eight

    * Layers - Platformer tutorial: platformer_part_eight
    * Multiple Levels - sprite_tiled_map_with_levels
    * Object Layer - *Supported, but documentation needed.*
    * Hit-boxes - *Supported, but documentation needed.*
    * Animated Tiles - *Supported, but documentation needed.*

* Sound - `Learn Arcade book sound chapter <https://learn.arcade.academy/en/latest/chapters/20_sounds/sounds.html>`_

  * music_control_demo
  * Spatial sound sound_demo

* Particles - particle_systems
* GUI

  * Concepts - gui_concepts
  * Examples - gui_concepts

* OpenGL

  * Read more about using OpenGL in Arcade with open_gl_notes.
  * Lights - light_demo
  * Writing shaders using "ShaderToy"

    * shader_toy_tutorial_glow
    * shader_toy_tutorial_particles
    * Learn how to ray-cast shadows in the raycasting_tutorial.
    * Make your screen look like an 80s monitor in crt_filter.
    * Study the `Asteroids Example Code <https://github.com/pythonarcade/asteroids>`_.

  * Rendering onto a sprite to create a mini-map - minimap
  * Bloom/glow effect - bloom_defender
  * Learn to do a compute shader in compute_shader_tutorial.

* Logging
