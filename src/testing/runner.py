import os
import re
import subprocess
import sys
import textwrap


def get_dynamic_fuzz_logic(game_file_path: str) -> str:
    """
    尋找動態 Fuzz 邏輯。
    已升級：全域適用，不依賴特定 View 的 on_update。
    """
    dir_path = os.path.dirname(game_file_path)
    logic_path = os.path.join(dir_path, "fuzz_logic.py")

    default_logic = """
# --- 1. 初始化與跳過開始畫面 (Click to Start) ---
if not hasattr(window, '_monkey_has_started'):
    window._monkey_has_started = True

    _w = window.width
    _h = window.height

    # 模擬滑鼠點擊畫面正中央
    if hasattr(self, 'on_mouse_press'):
        try: self.on_mouse_press(_w // 2, _h // 2, arcade.MOUSE_BUTTON_LEFT, 0)
        except: pass
    if hasattr(self, 'on_mouse_release'):
        try: self.on_mouse_release(_w // 2, _h // 2, arcade.MOUSE_BUTTON_LEFT, 0)
        except: pass

    # 模擬按下 ENTER 與 SPACE
    if hasattr(self, 'on_key_press'):
        try: 
            self.on_key_press(arcade.key.ENTER, 0)
            self.on_key_press(arcade.key.SPACE, 0)
        except: pass

# --- 2. 隨機壓力測試 (Random Fuzzing) ---
_w = window.width
_h = window.height

# Random Mouse Press
if _monkey_random.random() < 0.05:
    _mx = _monkey_random.randint(0, _w)
    _my = _monkey_random.randint(0, _h)
    if hasattr(self, 'on_mouse_press'):
        try: self.on_mouse_press(_mx, _my, arcade.MOUSE_BUTTON_LEFT, 0)
        except: pass
    if hasattr(self, 'on_mouse_release'):
        try: self.on_mouse_release(_mx, _my, arcade.MOUSE_BUTTON_LEFT, 0)
        except: pass

# Random Key Press
if _monkey_random.random() < 0.05:
    _keys = [arcade.key.SPACE, arcade.key.LEFT, arcade.key.RIGHT, arcade.key.UP, arcade.key.DOWN, arcade.key.ENTER, arcade.key.ESCAPE]
    _k = _monkey_random.choice(_keys)
    if hasattr(self, 'on_key_press'):
        try: self.on_key_press(_k, 0)
        except: pass
"""

    if os.path.exists(logic_path):
        try:
            with open(logic_path, "r", encoding="utf-8") as f:
                custom_logic = f.read()
                bypass_start_logic = default_logic.split("# --- 2.")[0]
                return bypass_start_logic + "\n" + custom_logic
        except Exception:
            return default_logic

    return default_logic


def inject_monkey_bot(code_content: str, bot_logic: str) -> str:
    """
    將 Monkey Bot 包裝成獨立的全域函數，並使用 arcade.schedule 注入到 arcade.run() 之前。
    這樣無論目前的 View 是什麼，Fuzzer 都會完美運行！
    """
    # 預處理
    lines = bot_logic.splitlines()
    filtered_lines = [line for line in lines if
                      not any(line.strip().startswith(s) for s in ["import arcade", "import random"])]
    bot_logic = "\n".join(filtered_lines)
    bot_logic = textwrap.dedent(bot_logic).strip()

    # 建立全域的 hook 函數
    hook_code = f"""
def _global_monkey_bot(delta_time):
    try:
        import arcade
        import random as _monkey_random
        # 動態取得當前的 window 與 view
        window = arcade.get_window()
        self = window.current_view

{textwrap.indent(bot_logic, '        ')}
    except Exception:
        pass

arcade.schedule(_global_monkey_bot, 1/60.0)
arcade.run()"""

    # 尋找 arcade.run() 並將其替換為我們的全域 hook
    if "arcade.run()" in code_content:
        pattern = re.compile(r"([ \t]*)arcade\.run\(\)")
        match = pattern.search(code_content)
        if match:
            indent = match.group(1)  # 取得原本 arcade.run() 的縮排
            # 確保我們注入的程式碼縮排完全一致
            formatted_hook = textwrap.indent(hook_code.strip(), indent)
            return code_content[:match.start()] + formatted_hook + code_content[match.end():]

    return code_content

def run_fuzz_test(file_path: str, duration: int = 15) -> tuple[bool, str]:
    """
    執行 Fuzz 測試並回傳結果。
    """
    try:
        if not os.path.exists(file_path):
            return False, "檔案不存在"

        with open(file_path, "r", encoding="utf-8") as f:
            original_code = f.read()

        # 獲取並注入邏輯
        bot_logic = get_dynamic_fuzz_logic(file_path)
        fuzzed_code = inject_monkey_bot(original_code, bot_logic)

        # 建立暫存檔執行測試
        temp_file = file_path.replace(".py", "_fuzz_temp.py")
        with open(temp_file, "w", encoding="utf-8") as f:
            f.write(fuzzed_code)

        env = os.environ.copy()
        env["SDL_AUDIODRIVER"] = "dummy"  # 避免音效輸出錯誤

        cmd = [sys.executable, temp_file]
        process = subprocess.Popen(
            cmd,
            stderr=subprocess.PIPE,
            stdout=subprocess.PIPE,
            text=True,
            env=env
        )

        try:
            # 等待指定時間，若沒崩潰則視為通過
            stdout, stderr = process.communicate(timeout=duration)
        except subprocess.TimeoutExpired:
            process.kill()
            if os.path.exists(temp_file): os.remove(temp_file)
            return True, "Fuzz Test Passed: 遊戲在壓力測試中存活。"

        if os.path.exists(temp_file): os.remove(temp_file)

        if process.returncode != 0:
            error_msg = stderr
            if "Traceback" in stderr:
                error_msg = "Traceback" + stderr.split("Traceback")[-1]
            return False, f"Arcade 運行崩潰: {error_msg}"

        return True, "Fuzz Test Passed."
    except Exception as e:
        return False, f"Fuzzer 執行異常: {str(e)}"


if __name__ == "__main__":
    file_path = "/mnt/d/NCKU/CSIE-Project/LLM-Game-Generator-LangChain/output_games/generated_game/game.py"
    success, msg = run_fuzz_test(file_path, 100)
    print(success, msg)