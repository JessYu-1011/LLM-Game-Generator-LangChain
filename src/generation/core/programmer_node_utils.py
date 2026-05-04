import json
import os
import re

from src.generation.core.chains import ArcadeAgentChain
from src.generation.core.game_state import GameState
from src.generation.picture_generate import picture_generate
from src.prompts.game_logic_cheat_sheet import PHYSICS_MATH_CHEAT_SHEET, GRID_MATH_CHEAT_SHEET, PLATFORMER_CHEAT_SHEET

def _programmer_node_math_injection(state: GameState, log_callback) -> str:
    """
    =================== Math related prompts injection ===========================
    """
    math_injection = ""
    gdd_lower = state["gdd"].lower()
    if any(k in gdd_lower for k in ["pool", "billiard", "physics", "ball", "shooter", "tank"]):
        log_callback("[System] Detected Physics/Top-Down Game. Injecting Vector Math...")
        math_injection = PHYSICS_MATH_CHEAT_SHEET
    elif any(k in gdd_lower for k in ["grid", "2048", "tetris", "snake", "puzzle", "board"]):
        log_callback("[System] Detected Grid-Based Game. Injecting Grid Math...")
        math_injection = GRID_MATH_CHEAT_SHEET
    elif any(k in gdd_lower for k in ["jump", "platform", "gravity", "flappy", "mario"]):
        log_callback("[System] Detected Platformer. Injecting Gravity Logic...")
        math_injection = PLATFORMER_CHEAT_SHEET

    return math_injection


def _programmer_node_choose_templates(state: GameState, agents: ArcadeAgentChain, prompt_compress_agents, log_callback) -> list:
    """
    ========================= Choose which templates to use ==============================
    """
    log_callback("[Programmer] AI deciding on required templates...")
    needed_templates = []
    try:
        log_callback("[Programmer] Extracting core mechanics for template decision...")
        token_tracker = agents.get_token_tracker()
        with token_tracker.track_step("compress_gdd"):
            compressed_gdd = prompt_compress_agents.get_gdd_mechanics_extractor().invoke({"gdd": state["gdd"]})
        resp = agents.get_template_decision_chain().invoke({"gdd": compressed_gdd})

        match = re.search(r'\[.*?\]', resp, re.DOTALL)
        if match:
            parsed_list = json.loads(match.group(0))
            needed_templates = [t for t in parsed_list if t in ["menu.py", "camera.py", "asset_manager.py"]]
        if not needed_templates:
            needed_templates = ["asset_manager.py", "camera.py", "menu.py"]
    except Exception as e:
        log_callback(f"[Programmer] [Warning] Template decision failed, using defaults. Error: {e}")
        needed_templates = ["asset_manager.py", "camera.py", "menu.py"]

    log_callback(f"[Programmer] Selected templates: {needed_templates}")

    return needed_templates


def _programmer_node_templates_inject_prompts(needed_templates: list, log_callback) -> list[list | list | str ]:
    template_code_blocks = []
    guaranteed_imports = []
    template_instructions = ""
    template_injection_prompt = ""

    root_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "../.."))
    template_dir = os.path.join(root_dir, "generation", "template")

    for t_file in needed_templates:
        t_path = os.path.join(template_dir, t_file)
        if os.path.exists(t_path):
            with open(t_path, "r", encoding="utf-8") as f:
                template_code_blocks.append([t_file, f.read()])

            if "asset_manager" in t_file:
                guaranteed_imports.append("from asset_manager import AssetManager")
                template_instructions += (
                    "**AssetManager (MANDATORY)**: NEVER use `arcade.load_texture`. NEVER use `arcade.create_soft_texture`. NEVER use `arcade.texture`. ALWAYS load sprites like this:\n"
                    "`self.texture = AssetManager.get_texture('player', fallback_color=arcade.color.RED, width=32, height=32)`\n\n"
                    "**ASSET DESCRIPTION**: Immediately after each get_texture call, write a short, concrete text description of the asset for image generation.\n"
                    "- Must be one line only.\n"
                    "- Must clearly describe what the sprite should look like.\n"
                    "- Example: `# DESCRIPTION: a brave knight in shining armor wielding a sword`\n"
                    "- Always include this DESCRIPTION comment for every asset.\n\n"
                )
            elif "camera" in t_file:
                guaranteed_imports.append("from camera import FollowCamera")
                template_instructions += "- **Scrolling (MANDATORY)**: Use `FollowCamera` for scrolling levels. Usage:\n  * Init: `self.camera = FollowCamera(SCREEN_WIDTH, SCREEN_HEIGHT, map_width, map_height)`\n  * Draw: Call `self.camera.use()` before drawing world sprites. Call `self.ui_camera.use()` for HUD.\n  * Update: Call `self.camera.update_to_target(self.player)` in `on_update`.\n"
            elif "menu" in t_file:
                guaranteed_imports.append("from menu import PauseView")
                template_instructions += "- **Pause System (MANDATORY)**: DO NOT write `self.paused = True`. Instead, handle ESC key like this:\n  `if key == arcade.key.ESCAPE: self.window.show_view(PauseView(self))`\n"
        else:
            log_callback(f"[Programmer] [Warning] Template file not found: {t_path}")

    imports_str = "\n".join(guaranteed_imports)
    if template_instructions:
        template_injection_prompt = (
            "\n=======================================================\n"
            "🔥 CRITICAL: PRE-BUILT MODULES REQUIREMENT 🔥\n"
            "=======================================================\n"
            "I have already created the template files for you. You MUST use them in `game.py`!\n\n"
            "1. YOU MUST PUT THESE IMPORTS AT THE VERY TOP OF `game.py`:\n"
            "```python\n"
            f"{imports_str}\n"
            "```\n\n"
            "2. YOU MUST FOLLOW THESE IMPLEMENTATION RULES:\n"
            f"{template_instructions}\n"
            "Failure to use these classes will result in immediate system crash!\n"
            "=======================================================\n"
        )

    return [template_code_blocks, guaranteed_imports, template_injection_prompt]


def _programmer_node_constraints(state: GameState, log_callback) -> str:
    """
   ==================== Constraints for generating the codes =============================
   """
    log_callback("[Programmer] Implementing game.py with RAG, Math & Templates...")
    complexity_constraints = (
        "1. Write verbose code with detailed comments.\n"
        "2. Implement at least 3 different enemy types or obstacles if applicable.\n"
        "3. Include a 'ParticleManager' class for visual effects.\n"
        "4. ABSOLUTELY NO ABBREVIATED CODE. WRITE EVERY LINE.\n"
        "5. Implement a proper Game Over view and Restart mechanic."
    )
    constraints = "\n".join(state["architecture_plan"].get('constraints', []))
    assets_str = state.get("assets_json", "{}")
    full_constraints = (
        f"=== AVAILABLE ASSETS FROM ART DIRECTOR ===\n"
        f"You MUST strictly use the texture names defined in this JSON. DO NOT invent new ones.\n"
        f"{assets_str}\n\n"
        f"=== CONSTRAINTS ===\n"
        f"{constraints}\n\n{complexity_constraints}"
    )
    return full_constraints

def _programmer_node_extract_safe_constants(code: str) -> dict:
    """
    Extract all capital constants from code
    """
    #  搜尋最終程式碼中所有的圖片請求, 並從fallback size計算圖片大小, 可處理fallback size為常數和危險的格式(example : WIDTH = __import__("os").system("rm -rf /"))
    constants = dict(re.findall(r"([A-Z_][A-Z0-9_]*)\s*=\s*(.+)", code))
    safe_env = {}
    for name, expr in constants.items():
        try:
            safe_env[name] = eval(expr, {"__builtins__": None}, safe_env)
        except:
            pass
    return safe_env

def _programmer_node_generate_images_from_code(code: str, safe_env: dict, log_callback):
    """
    Search get_texture and call graph generation
    """
    pattern = r"get_texture\(\s*'([^']+)'.*?width\s*=\s*([^,\s)]+).*?height\s*=\s*([^\s,)]+)\s*\)[\s\S]*?#\s*DESCRIPTION:\s*([^\n]+)"
    matches = re.findall(pattern, code, re.DOTALL)

    for match in matches:
        if len(match) != 4: continue
        name, width_str, height_str, description = match

        # 安全解析 Width
        try:
            # 先嘗試用 safe_env 算出來
            final_width = int(eval(width_str, {"__builtins__": None}, safe_env))
        except:
            try:
                # 算不出來，嘗試直接轉整數
                final_width = int(width_str)
            except:
                # 轉整數也失敗，給予預設值 64
                log_callback(f"[Warning] Cannot parse width '{width_str}' for '{name}'. Using fallback 64.")
                final_width = 64

        # 安全解析 Height (同樣的邏輯保護)
        try:
            final_height = int(eval(height_str, {"__builtins__": None}, safe_env))
        except:
            try:
                final_height = int(height_str)
            except:
                log_callback(f"[Warning] Cannot parse height '{height_str}' for '{name}'. Using fallback 64.")
                final_height = 64

        size = [final_width, final_height]
        picture_generate(name, description, size, log_callback)

def _programmer_node_apply_import_failsafe(code: str, imports: list, log_callback) -> str:
    """
    Ensure all necessary modules are imported
    """
    for imp in imports:
        if imp not in code:
            log_callback(f"[Failsafe] Auto-injecting missing import: {imp}")
            if "import arcade" in code:
                code = code.replace("import arcade", f"import arcade\n{imp}")
            else:
                code = f"import arcade\n{imp}\n{code}"
    return code