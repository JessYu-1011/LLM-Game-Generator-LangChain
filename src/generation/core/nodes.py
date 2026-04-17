import os
import json
import re
import sys
import traceback

from src.generation.asset_gen import generate_assets
from src.prompts.game_logic_cheat_sheet import PHYSICS_MATH_CHEAT_SHEET, GRID_MATH_CHEAT_SHEET, PLATFORMER_CHEAT_SHEET
from src.generation.core.game_state import GameState
from src.utils import clean_code_content, save_generated_files

def ceo_node(state: GameState, agents, log_callback):
    log_callback(f"[Design] CEO Analyzing idea: {state['user_input']}...")
    analysis = agents.get_ceo_chain().invoke({"input": state["user_input"]})
    return {"ceo_analysis": analysis, "design_iterations": 0, "design_feedback": "None"}

def cpo_node(state: GameState, agents, log_callback):
    log_callback(f"[Design] CPO Drafting GDD (Round {state['design_iterations'] + 1})...")
    gdd = agents.get_cpo_chain().invoke({
        "idea": state["user_input"],
        "analysis": state["ceo_analysis"],
        "feedback": state["design_feedback"]
    })
    return {"gdd": gdd}

def design_reviewer_node(state: GameState, agents, log_callback):
    log_callback("[Design] Reviewer critiquing GDD...")
    feedback = agents.get_reviewer_chain().invoke({"gdd": state["gdd"]})
    return {
        "design_feedback": feedback,
        "design_iterations": state["design_iterations"] + 1
    }

def asset_node(state: GameState, log_callback, provider_name):
    log_callback("[System] Generating Assets...")
    assets = generate_assets(gdd_context=state["gdd"], provider=provider_name)
    return {"assets_json": assets}

def architect_node(state: GameState, agents, log_callback):
    log_callback(f"[Architect] Planning system architecture (Round {state['plan_iterations'] + 1})...")
    if state['plan_iterations'] == 0:
        plan = agents.get_architect_chain().invoke({
            "gdd": state["gdd"],
            "assets": state["assets_json"],
            "format_instructions": agents.json_parser.get_format_instructions()
        })
    else:
        log_callback("[Architect] Refining plan based on feedback...")
        plan_str = json.dumps(state["architecture_plan"], indent=2)
        plan = agents.get_architect_refinement_chain().invoke({
            "original_plan": plan_str,
            "feedback": state["plan_feedback"],
            "format_instructions": agents.json_parser.get_format_instructions()
        })
    return {"architecture_plan": plan}

def plan_reviewer_node(state: GameState, agents, log_callback):
    log_callback("[Architect] Plan Review...")
    plan_str = json.dumps(state["architecture_plan"], indent=2)
    feedback = agents.get_plan_reviewer_chain().invoke({"plan": plan_str})
    return {
        "plan_feedback": feedback,
        "plan_iterations": state["plan_iterations"] + 1
    }

def programmer_node(state: GameState, agents, prompt_compress_agents, log_callback, work_dir):
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

    log_callback("[Programmer] AI deciding on required templates...")
    needed_templates = []
    try:
        log_callback("[Programmer] Extracting core mechanics for template decision...")
        compressed_gdd = prompt_compress_agents.get_gdd_mechanics_extractor().invoke({"gdd": state["gdd"]})
        resp = agents.get_template_decision_chain().invoke({"gdd": compressed_gdd})

        match = re.search(r'\[.*?\]', resp, re.DOTALL)
        if match:
            parsed_list = json.loads(match.group(0))
            needed_templates = [t for t in parsed_list if t in ["menu.py", "camera.py", "asset_manager.py"]]
        if not needed_templates:
            needed_templates = ["asset_manager.py", "camera.py", "menu.py"]
    except Exception as e:
        log_callback(f"[Warning] Template decision failed, using defaults. Error: {e}")
        needed_templates = ["asset_manager.py", "camera.py", "menu.py"]

    log_callback(f"[Programmer] Selected templates: {needed_templates}")

    template_code_blocks = []
    guaranteed_imports = []
    template_instructions = ""

    root_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "../.."))
    template_dir = os.path.join(root_dir, "generation", "template")

    for t_file in needed_templates:
        t_path = os.path.join(template_dir, t_file)
        if os.path.exists(t_path):
            with open(t_path, "r", encoding="utf-8") as f:
                template_code_blocks.append([t_file, f.read()])

            if "asset_manager" in t_file:
                guaranteed_imports.append("from asset_manager import AssetManager")
                template_instructions += "- **Asset Loading (MANDATORY)**: NEVER use `arcade.load_texture`. ALWAYS use `AssetManager` like this:\n  `self.texture = AssetManager.get_texture('player.png', fallback_color=arcade.color.RED, width=32, height=32)`\n"
            elif "camera" in t_file:
                guaranteed_imports.append("from camera import FollowCamera")
                template_instructions += "- **Scrolling (MANDATORY)**: Use `FollowCamera` for scrolling levels. Usage:\n  * Init: `self.camera = FollowCamera(SCREEN_WIDTH, SCREEN_HEIGHT, map_width, map_height)`\n  * Draw: Call `self.camera.use()` before drawing world sprites. Call `self.ui_camera.use()` for HUD.\n  * Update: Call `self.camera.update_to_target(self.player)` in `on_update`.\n"
            elif "menu" in t_file:
                guaranteed_imports.append("from menu import PauseView")
                template_instructions += "- **Pause System (MANDATORY)**: DO NOT write `self.paused = True`. Instead, handle ESC key like this:\n  `if key == arcade.key.ESCAPE: self.window.show_view(PauseView(self))`\n"
        else:
            log_callback(f"[Warning] Template file not found: {t_path}")

    imports_str = "\n".join(guaranteed_imports)
    template_injection_prompt = ""
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

    log_callback("[Programmer] Implementing game.py with RAG, Math & Templates...")
    complexity_constraints = (
        "1. Write verbose code with detailed comments.\n"
        "2. Implement at least 3 different enemy types or obstacles if applicable.\n"
        "3. Include a 'ParticleManager' class for visual effects.\n"
        "4. ABSOLUTELY NO ABBREVIATED CODE. WRITE EVERY LINE.\n"
        "5. Implement a proper Game Over view and Restart mechanic."
    )
    constraints = "\n".join(state["architecture_plan"].get('constraints', []))
    full_constraints = f"{constraints}\n\n{complexity_constraints}"

    response = agents.get_programmer_chain().invoke({
        "architecture_plan": state["architecture_plan"],
        "review_feedback": state["plan_feedback"],
        "constraints": full_constraints,
        "math_context": math_injection
    })

    content = response.content if hasattr(response, 'content') else str(response)
    cleaned_code = clean_code_content(content)

    for imp in guaranteed_imports:
        if imp not in cleaned_code:
            log_callback(f"[Failsafe] LLM forgot to import '{imp}'. Auto-injecting...")
            if "import arcade" in cleaned_code:
                cleaned_code = cleaned_code.replace("import arcade", f"import arcade\n{imp}")
            else:
                cleaned_code = f"import arcade\n{imp}\n" + cleaned_code

    log_callback("[Test] Generating Fuzzer logic snippet...")
    fuzzer_response = agents.get_fuzzer_chain().invoke({"gdd": state["gdd"]})
    fuzzer_logic = fuzzer_response.content if hasattr(fuzzer_response, 'content') else str(fuzzer_response)
    cleaned_fuzzer_logic = clean_code_content(fuzzer_logic)

    project_files = {"game.py": cleaned_code, "fuzz_logic.py": cleaned_fuzzer_logic}
    for t_file, code in template_code_blocks:
        project_files[t_file] = code

    save_generated_files(project_files, work_dir)

    return {
        "current_code": cleaned_code,
        "project_files": project_files,
        "test_iterations": 0,
        "test_errors": [],
        "is_valid": False
    }

def evaluator_node(state: GameState, agents, log_callback, work_dir):
    log_callback(f"\n[Test] Starting validation round {state['test_iterations'] + 1}...")
    current_code = state["current_code"]
    main_file_path = os.path.join(work_dir, "game.py")
    lines_of_traceback_included = 10

    log_callback("[Check] Running static syntax check...")
    try:
        compile(current_code, "game.py", 'exec')
        log_callback("[Check] Syntax validation passed.")
    except SyntaxError as e:
        error_msg = f"[SyntaxError] Line {e.lineno}: {e.msg}\n{e.text}"
        log_callback("[Check] Syntax error detected.")
        return {"test_errors": state.get("test_errors", []) + [error_msg]}

    log_callback("[Test] Running fuzzer runtime tests...")
    try:
        root_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "../.."))
        if root_dir not in sys.path:
            sys.path.append(root_dir)
        from src.testing.runner import run_fuzz_test

        success, error_msg = run_fuzz_test(main_file_path, duration=30)
        if not success:
            log_callback(f"[Test] Fuzzer Runtime Error: {error_msg}")
            return {"test_errors": state.get("test_errors", []) + [f"[RuntimeError] {error_msg}"]}
        else:
            log_callback("[Test] Fuzzer passed (No crashes for 30s).")

    except Exception as e:
        log_callback(f"[Error] Test runner exception: {str(e)}")
        short_error = traceback.format_exc().strip().split('\n')[-lines_of_traceback_included:]
        error_msg = f"[TestRunnerError]: {' '.join(short_error)}"
        return {"test_errors": state.get("test_errors", []) + [error_msg]}

    log_callback("[Review] Running strict API standard review...")
    review_result = agents.get_logic_reviewer_chain().invoke({"code": current_code})

    if "PASS" not in review_result:
        error_msg = f"[LogicError] {review_result}"
        log_callback(f"[Review] Logic/API Rule Violation: {review_result}")
        return {"test_errors": state.get("test_errors", []) + [error_msg]}
    else:
        log_callback("[Review] Strict API validation passed.")

    log_callback("[Result] Code passed ALL validations successfully!")
    return {"is_valid": True}

def fixer_node(state: GameState, agents, prompt_compress_agents, log_callback, work_dir):
    log_callback("[Fixer] Reading historical error logs and attempting fix...")
    latest_error = state["test_errors"][-1]

    history_errors = state["test_errors"][:-1]
    error_prompt = latest_error
    if history_errors:
        compressed_history = prompt_compress_agents.compress_errors(history_errors)
        error_prompt = f"[Past Failed Attempts (Do NOT repeat these mistakes)]:\n{compressed_history}\n\n[Latest Error]:\n{latest_error}"

    if "[LogicError]" in latest_error:
        response = agents.get_logic_fixer_chain().invoke({
            "code": state["current_code"],
            "error": error_prompt,
            "gdd": state["gdd"]
        })
    else:
        response = agents.get_syntax_fixer_chain().invoke({
            "code": state["current_code"],
            "error": error_prompt
        })

    updated_code = clean_code_content(response)

    with open(os.path.join(work_dir, "game.py"), "w", encoding="utf-8") as f:
        f.write(updated_code)

    new_project_files = state["project_files"]
    new_project_files["game.py"] = updated_code

    return {
        "current_code": updated_code,
        "project_files": new_project_files,
        "test_iterations": state["test_iterations"] + 1
    }


def check_design_loop(state: GameState):
    return "continue_to_asset" if state["design_iterations"] >= 2 else "back_to_cpo"

def check_plan_loop(state: GameState):
    return "continue_to_programmer" if state["plan_iterations"] >= 2 else "back_to_architect"

def check_test_loop(state: GameState):
    if state["is_valid"]:
        return "success"
    if state["test_iterations"] >= 5:
        return "failure"
    return "go_to_fixer"