Source: Arcade 2.6.17 doc/gui/troubleshooting.rst



Troubleshooting & Hints
^^^^^^^^^^^^^^^^^^^^^^^

`UILabel` does not show the text after it was updated
............................................................

Currently the size of `UILabel` is not updated after modifying the text.
Due to the missing information, if the size was set by the user before, this behaviour is intended for now.
To adjust the size to fit the text you can use :meth:`UILabel.fit_content`.

In the future this might be fixed.
