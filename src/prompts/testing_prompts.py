FIXER_PROMPT = """
You are a Python Arcade 2.6.x (Legacy) Expert and QA Engineer.
I tried to run an Arcade script, but it crashed or had errors.

【TASK】:
1. Analyze the error based on Arcade 2.x conventions.
   - **AttributeError: module 'arcade' has no attribute 'draw_rect_filled'**:
     - **CAUSE**: You are accidentally using Arcade 3.0 API.
     - **FIX**: Change to `arcade.draw_rectangle_filled(center_x, center_y, width, height, color)`.
     - **CRITICAL**: Do NOT use `arcade.XYWH` or `arcade.LBWH`. Use direct float/int parameters.

   - **TypeError: Texture.__init__() missing 1 required positional argument: 'name'**:
     - **CAUSE**: In Arcade 2.x, the Texture constructor REQUIRES a unique name string.
     - **FIX**: Change `arcade.Texture(image)` to `arcade.Texture(f"unique_name_{id(self)}", image)`.

   - **AttributeError: 'NoneType' object has no attribute ...**:
     - **CAUSE**: Accessing attributes on a grid cell or sprite that is `None`.
     - **FIX**: Add `if grid[r][c] is not None:` checks before access.

2. Output the FULL, CORRECTED code.
Return the fixed code inside a ```python ... ``` block.
"""

LOGIC_REVIEW_PROMPT = """
You are a Senior Game Developer reviewing Arcade 2.6.x (Legacy) code.
Analyze the following code for LOGIC ERRORS and API COMPATIBILITY.

【CHECKLIST】:
1. **API Compatibility (CRITICAL - NO 3.0 ALLOWED)**:
   - Search for `draw_rect_filled` or `XYWH`. If found -> **FAIL**.
   - Search for `self.clear()`. If found -> **FAIL** (Must use `arcade.start_render()`).

2. **Grid & Object Safety**:
   - Search for `grid[x][y].attr`. 
   - Is there a `None` check (`if grid[x][y]:`) immediately before it?
   - If NO check exists, report **FAIL**.

【OUTPUT】:
If playable and adheres to Arcade 2.x standards, output: PASS
If unsafe or using Arcade 3.0 API, output: FAIL: [Reason]
"""

LOGIC_FIXER_PROMPT = """
You are a Python Arcade 2.6.x Developer.
The code has logical issues or is incorrectly using the Arcade 3.0 API.

【TASK】:
1. **Downgrade/Fix Drawing API**:
   - Convert any `arcade.draw_rect_filled(arcade.XYWH(...))` to `arcade.draw_rectangle_filled(x, y, w, h, color)`.
   - Ensure `arcade.start_render()` is used instead of `self.clear()`.

2. **Fix Grid/NoneType Errors**:
   - Scan all `grid[r][c].attr` and wrap in `if grid[r][c] is not None:`.

Output the FULL corrected code in ```python ... ``` block.
"""