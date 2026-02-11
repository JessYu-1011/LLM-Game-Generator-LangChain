Source: Arcade 2.6.17 doc/gl/index.rst


# Arcade OpenGL API

This is the low level rendering API in Arcade and is used
internally for all drawing/rendering. It's a higher level
wrapper over OpenGL 3.3+ core and gives the user easy
access to GPU programs (shaders), textures, framebuffers,
queries, buffers, vertex arrays/geometry and compute shaders
(Note that compute shaders are not supported on MacOS).

This API is also heavily inspired by ModernGL_. It's basically
a subset of ModernGL_ except we are using pyglet's
OpenGL bindings. However, we don't have the context
flexibility and speed of ModernGL_, but we are at the
very least on par with PyOpenGL or slightly better because
pyglet's OpenGL bindings are very light. The higher
level abstraction is the main selling point as it
saves the user from an enormous amount of work.

Note that all resources are created through the
:py`arcade.gl.Context` / :py`arcade.ArcadeContext`.
An instance of this type should be accessible the window
(:py:attr:`arcade.Window.ctx`).

This API can also be used with pyglet by creating an instance
of :py`arcade.gl.Context` after the window creation.
The :py`arcade.ArcadeContext` on the other hand
extends the default Context with arcade specific helper methods
and should only be used by arcade.

Some prior knowledge of OpenGL might be needed to understand
how this API works, but we do have examples in the experimental
directory (git).

   :maxdepth: 2

   context
   texture
   buffer
   buffer_description
   geometry
   framebuffer
   query
   program
   compute_shader
   exceptions

