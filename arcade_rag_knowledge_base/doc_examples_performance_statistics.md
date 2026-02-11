Source: Arcade 2.6.17 doc/examples/performance_statistics.rst

:orphan:


# Performance Statistics


You can easily include graphs that show FPS, or how long it takes dispatched events to process.
See perf_info_api.

You can also print out the count and average time for all dispatched events with the `arcade.print_timings`
function. The output of that function looks like:


```text

    Event          Count Average Time
    -------------- ----- ------------
    on_activate        1       0.0000
    on_resize          1       0.0000
    on_show            1       0.0000
    update            59       0.0030
    on_update         59       0.0000
    on_expose          1       0.0000
    on_draw           59       0.0021
    on_mouse_enter     1       0.0000
    on_mouse_motion  100       0.0000

    :caption: performance_statistics.py
    :linenos:
    :emphasize-lines: 26, 90-109, 120-125, 131-134

