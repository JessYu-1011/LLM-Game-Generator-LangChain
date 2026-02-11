Source: Arcade 2.6.17 doc/install/source.rst

# Installation From Source

First step is to clone the repository:


```bash

    git clone https://github.com/pythonarcade/arcade.git

Or download from:

    https://github.com/pythonarcade/arcade/archive/master.zip

Next, we'll create a linked install. This will allow you to change files in the
arcade directory, and is great
if you want to modify the Arcade library code. From the root directory of
arcade type:


```bash

    pip install -e .

To install additional documentation and development requirements:


```bash

    pip install -e .[dev]

