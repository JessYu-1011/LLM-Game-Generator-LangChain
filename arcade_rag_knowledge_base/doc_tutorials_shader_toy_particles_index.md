Source: Arcade 2.6.17 doc/tutorials/shader_toy_particles/index.rst


# Shader Toy Tutorial - Particles



    <iframe width="560" height="315" src="https://www.youtube.com/embed/99AAAzf5ndY" title="YouTube video player" frameborder="0" allow="accelerometer; autoplay; clipboard-write; encrypted-media; gyroscope; picture-in-picture" allowfullscreen></iframe>

This tutorial assumes you are already familiar with the material in shader_toy_tutorial_glow.
In this tutorial,
we take a look at adding animated particles. These particles can be used for an explosion
effect.

The "trick" to
this example, is the use of pseudo-random numbers to generate each particle's angle and speed from
the initial explosion point. Why "pseudo-random"? This allows each processor on the GPU
to independently calculate each particle's position at any point and time. We can then
allow the GPU to calculate in parallel.

## Load the shader

First, we need a program that will load a shader. This program is also keeping track
of how much time has elapsed. This is necessary for us to calculate how far along the animation
sequence we are.

   :linenos:


## Initial shader with particles

   :width: 50%

   :linenos:
   :language: glsl

## Add particle movement


   :linenos:
   :language: glsl
   :emphasize-lines: 13-14, 50-51

## Fade-out

   :linenos:
   :language: glsl
   :emphasize-lines: 59


## Glowing Particles


   :linenos:
   :language: glsl
   :emphasize-lines: 15-16, 57-58

## Twinkling Particles

   :linenos:
   :language: glsl
   :emphasize-lines: 60
