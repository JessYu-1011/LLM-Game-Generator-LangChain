Source: Arcade 2.6.17 doc/examples/platform_tutorial/step_01.rst



## Step 1 - Install and Open a Window

Our first step is to make sure everything is installed, and that we can at least
get a window open.

Installation
~~~~~~~~~~~~
* Make sure Python is installed. `Download Python here <https://www.python.org/downloads/>`_
  if you don't already have it.

* Make sure the `Arcade library <https://pypi.org/project/arcade/>`_ is installed.

  * You should first setup a virtual environment (venv) and activate it.
  * Install Arcade with ``pip install arcade``.
  * Here are the longer, official installation-instructions.

I highly recommend using the free community edition of PyCharm as an editor.
If you do, see install-pycharm.


Open a Window
~~~~~~~~~~~~~

The example below opens up a blank window. Set up a project and get the code
below working. (It is also in the zip file as
``01_open_window.py``.)


  This is a fixed-size window. It is possible to have  a
  resizable_window or a full_screen_example, but there are more
  interesting things we can do first. Therefore we'll stick with a fixed-size
  window for this tutorial.

    :caption: 01_open_window.py - Open a Window
    :linenos:

You should end up with a window like this:

   :width: 75%

Once you get the code working, figure out how to adjust the code so you can:

* Change the screen size
* Change the title
* Change the background color

  * See the documentation for color
  * See the documentation for csscolor

* Look through the documentation for the `arcade.Window`
  class to get an idea of everything it can do.
