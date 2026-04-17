import os
import json
import sys
import re
import traceback

from langgraph.graph import StateGraph, START, END

from src.generation.game_state import GameState
from src.generation.chains import ArcadeAgentChain
from src.generation.asset_gen import generate_assets
from src.utils import clean_code_content, save_generated_files
from src.config import config
from src.prompts.game_logic_cheat_sheet import (
    PHYSICS_MATH_CHEAT_SHEET,
    GRID_MATH_CHEAT_SHEET,
    PLATFORMER_CHEAT_SHEET
)

from src.generation.prompt_compress_node import LocalPromptCompressor

def apply_deterministic_fix(original_code: str, start_line: int, end_line: int, replacement: str) -> str:
    """
    Replace the codes directly by:
    :param original_code: the original full codes
    :param start_line: starting line number
    :param end_line: ending line number
    :replacement: the replacement code
    :return the full fixed codes
    """

    # 1. slice the original code to a line by line list
    code_lines = original_code.split('\n')

    # 2. Clear the markdown marks
    clean_replacement = replacement.replace("```python=", "").replace("```python", "").replace("```", "").strip('\n')

    # 3. Dealing with the line number (starting from 1 to starting from 0)
    start_idx = start_line - 1
    end_idx = end_line

    # 4. combine the fixing codes
    new_code_lines = code_lines[:start_idx] + [clean_replacement] + code_lines[end_idx:]

    # 5. combine to str
    return '\n'.join(new_code_lines)

def create_game_generator_graph(agents: ArcadeAgentChain, prompt_compress_agents, log_callback, work_dir: str, provider_name:str="openai"):
    """
    Creates and returns a compiled LangGraph application.
    Passes 'agents' and 'log_callback' into the nodes via closure.
    """
    # --- Node Definitions ---
    def ceo_node(state: GameState):
        log_callback(f"[Design] CEO Analyzing idea: {state['user_input']}...")
        analysis = agents.get_ceo_chain().invoke({"input": state["user_input"]})
        return {"ceo_analysis": analysis, "design_iterations": 0, "design_feedback": "None"}

    def cpo_node(state: GameState):
        log_callback(f"[Design] CPO Drafting GDD (Round {state['design_iterations'] + 1})...")
        gdd = agents.get_cpo_chain().invoke({
            "idea": state["user_input"],
            "analysis": state["ceo_analysis"],
            "feedback": state["design_feedback"]
        })
        return {"gdd": gdd}

    def design_reviewer_node(state: GameState):
        log_callback("[Design] Reviewer critiquing GDD...")
        feedback = agents.get_reviewer_chain().invoke({"gdd": state["gdd"]})
        return {
            "design_feedback": feedback,
            "design_iterations": state["design_iterations"] + 1
        }

    def asset_node(state: GameState):
        log_callback("[System] Generating Assets...")
        assets = generate_assets(gdd_context=state["gdd"], provider=provider_name)
        return {"assets_json": assets}

    def architect_node(state: GameState):
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

    def plan_reviewer_node(state: GameState):
        log_callback("[Architect] Plan Review...")
        plan_str = json.dumps(state["architecture_plan"], indent=2)
        feedback = agents.get_plan_reviewer_chain().invoke({"plan": plan_str})
        return {
            "plan_feedback": feedback,
            "plan_iterations": state["plan_iterations"] + 1
        }

    def programmer_node(state: GameState):
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

        # ==========================================
        # AI Template Decision & Injection (Using Chain)
        # ==========================================
        log_callback("[Programmer] AI deciding on required templates...")

        needed_templates = []
        try:
            """ 
            Change from hard coded cutting the gdd into extraction
            Original:
            resp = agents.get_template_decision_chain().invoke({"gdd": state["gdd"][:1500]})
            """
            log_callback("[Programmer] Extracting core mechanics for template decision...")
            compressed_gdd = prompt_compress_agents.get_gdd_mechanics_extractor().invoke({"gdd": state["gdd"]})
            resp = agents.get_template_decision_chain().invoke({"gdd": compressed_gdd})

            match = re.search(r'\[.*?\]', resp, re.DOTALL)
            if match:
                parsed_list = json.loads(match.group(0))
                needed_templates = [t for t in parsed_list if t in ["menu.py", "camera.py", "asset_manager.py"]]
            if not needed_templates:
                needed_templates = ["asset_manager.py", "camera.py", "menu.py"]  # Fallback
        except Exception as e:
            log_callback(f"[Warning] Template decision failed, using defaults. Error: {e}")
            needed_templates = ["asset_manager.py", "camera.py", "menu.py"]

        log_callback(f"[Programmer] Selected templates: {needed_templates}")

        template_code_blocks = []
        guaranteed_imports = []  # 儲存必須出現的 imports
        template_instructions = ""

        # Parse template folder path
        root_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "../.."))
        template_dir = os.path.join(root_dir, "src", "generation", "template")

        for t_file in needed_templates:
            t_path = os.path.join(template_dir, t_file)
            if os.path.exists(t_path):
                with open(t_path, "r", encoding="utf-8") as f:
                    template_code_blocks.append(
                        [t_file, f.read()]
                    )

                # Give API Usage constraint (變得極度明確)
                if "asset_manager" in t_file:
                    guaranteed_imports.append("from asset_manager import AssetManager")
                    template_instructions += (
                        "- **Asset Loading (MANDATORY)**: NEVER use `arcade.load_texture`. ALWAYS use `AssetManager` like this:\n"
                        "  `self.texture = AssetManager.get_texture('player.png', fallback_color=arcade.color.RED, width=32, height=32)`\n"
                    )
                elif "camera" in t_file:
                    guaranteed_imports.append("from camera import FollowCamera")
                    template_instructions += (
                        "- **Scrolling (MANDATORY)**: Use `FollowCamera` for scrolling levels. Usage:\n"
                        "  * Init: `self.camera = FollowCamera(SCREEN_WIDTH, SCREEN_HEIGHT, map_width, map_height)`\n"
                        "  * Draw: Call `self.camera.use()` before drawing world sprites. Call `self.ui_camera.use()` for HUD.\n"
                        "  * Update: Call `self.camera.update_to_target(self.player)` in `on_update`.\n"
                    )
                elif "menu" in t_file:
                    guaranteed_imports.append("from menu import PauseView")
                    template_instructions += (
                        "- **Pause System (MANDATORY)**: DO NOT write `self.paused = True`. Instead, handle ESC key like this:\n"
                        "  `if key == arcade.key.ESCAPE: self.window.show_view(PauseView(self))`\n"
                    )
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
        # ==========================================

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

        # ==========================================
        # [NEW] Failsafe: 自動補全 LLM 漏掉的 Imports
        # ==========================================
        for imp in guaranteed_imports:
            if imp not in cleaned_code:
                log_callback(f"[Failsafe] LLM forgot to import '{imp}'. Auto-injecting...")
                if "import arcade" in cleaned_code:
                    # 插入在 import arcade 之後
                    cleaned_code = cleaned_code.replace("import arcade", f"import arcade\n{imp}")
                else:
                    # 如果連 import arcade 都沒有，直接加在最頂端
                    cleaned_code = f"import arcade\n{imp}\n" + cleaned_code

        # Generate Fuzzer Logic
        log_callback("[Test] Generating Fuzzer logic snippet...")
        fuzzer_response = agents.get_fuzzer_chain().invoke({"gdd": state["gdd"]})
        fuzzer_logic = fuzzer_response.content if hasattr(fuzzer_response, 'content') else str(fuzzer_response)
        cleaned_fuzzer_logic = clean_code_content(fuzzer_logic)

        project_files = {"game.py": cleaned_code, "fuzz_logic.py": cleaned_fuzzer_logic}
        for t_file, code in template_code_blocks:
            project_files[t_file] = code

        # Save files to disk for testing
        save_generated_files(project_files, work_dir)

        return {
            "current_code": cleaned_code,
            "project_files": project_files,
            "test_iterations": 0,
            "test_errors": [],
            "is_valid": False
        }

    def evaluator_node(state: GameState):
        """
        Validates the code in order of absolute truth:
        1. Syntax -> 2. Fuzzer (Runtime) -> 3. Static Logic Review
        """
        log_callback(f"\n[Test] Starting validation round {state['test_iterations'] + 1}...")
        current_code = state["current_code"]
        main_file_path = os.path.join(work_dir, "game.py")
        lines_of_traceback_included = 10
        # ==========================================
        # Stage A: Syntax Check (Fastest, catches typos)
        # ==========================================
        log_callback("[Check] Running static syntax check...")
        try:
            compile(current_code, "game.py", 'exec')
            log_callback("[Check] Syntax validation passed.")
        except SyntaxError as e:
            error_msg = f"[SyntaxError] Line {e.lineno}: {e.msg}\n{e.text}"
            log_callback("[Check] Syntax error detected.")
            return {"test_errors": [error_msg]}

        # ==========================================
        # Stage B: Runtime Test (Fuzzer) - THE GROUND TRUTH
        # ==========================================
        log_callback("[Test] Running fuzzer runtime tests...")
        try:
            root_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "../.."))
            if root_dir not in sys.path:
                sys.path.append(root_dir)
            from src.testing.runner import run_fuzz_test

            success, error_msg = run_fuzz_test(main_file_path, duration=30)
            if not success:
                log_callback(f"[Test] Fuzzer Runtime Error: {error_msg}")
                # Fuzzer errors are routed to the powerful Syntax/Traceback Fixer
                return {"test_errors": [f"[RuntimeError] {error_msg}"]}
            else:
                log_callback("[Test] Fuzzer passed (No crashes for 30s).")

        except Exception as e:
            import traceback
            log_callback(f"[Error] Test runner exception: {str(e)}")
            short_error = traceback.format_exc().strip().split('\n')[-lines_of_traceback_included:]
            error_msg = f"[TestRunnerError]: {' '.join(short_error)}"
            return {"test_errors": [error_msg]}

        # ==========================================
        # Stage C: Logic Review (Static Analysis)
        # ==========================================
        # Only runs if the game actually survives the Fuzzer!
        log_callback("[Review] Running strict API standard review...")
        review_result = agents.get_logic_reviewer_chain().invoke({"code": current_code})

        if isinstance(review_result, dict):
            status_str = str(review_result.get("status", "")).upper()
        else:
            try:
                parsed_json = json.loads(review_result)
                if isinstance(parsed_json, dict):
                    status_str = str(parsed_json.get("status", "")).upper()
                else:
                    status_str = str(review_result).upper()
            except json.JSONDecodeError:
                status_str = str(review_result).upper()

        if "PASS" not in status_str:
            error_msg = f"[LogicError] {review_result}"
            log_callback(f"[Review] Logic/API Rule Violation: {review_result}")
            # Logic Errors are routed to the Logic Fixer
            return {"test_errors": [error_msg]}
        else:
            log_callback("[Review] Strict API validation passed.")

        log_callback("[Result] Code passed ALL validations successfully!")
        return {"is_valid": True}

    def fixer_node(state: GameState):
        """Memory Core: Fixes code based on historical error logs."""
        log_callback("[Fixer] Reading historical error logs and attempting fix...")
        latest_error = state["test_errors"][-1]

        # Concatenate history to prevent the agent from repeating mistakes
        history_errors = state["test_errors"][:-1]
        error_prompt = latest_error
        if history_errors:
            compressed_history=prompt_compress_agents.compress_errors(history_errors)
            error_prompt = f"[Past Failed Attempts (Do NOT repeat these mistakes)]:\n{compressed_history}\n\n[Latest Error]:\n{latest_error}"

        # Route to appropriate fixer chain based on error type
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

        # Update file on disk for the next Fuzzer run
        with open(os.path.join(work_dir, "game.py"), "w", encoding="utf-8") as f:
            f.write(updated_code)

        # Update project files in state
        new_project_files = state["project_files"]
        new_project_files["game.py"] = updated_code

        return {
            "current_code": updated_code,
            "project_files": new_project_files,
            "test_iterations": state["test_iterations"] + 1
        }

    # --- Edge Conditional Functions ---

    def check_design_loop(state: GameState):
        return "continue_to_asset" if state["design_iterations"] >= 2 else "back_to_cpo"

    def check_plan_loop(state: GameState):
        return "continue_to_programmer" if state["plan_iterations"] >= 2 else "back_to_architect"

    def check_test_loop(state: GameState):
        if state["is_valid"]:
            return "success"
        if state["test_iterations"] >= 5:
            log_callback("[Warning] Max retries (5) reached, forcing termination of validation.")
            return "failure"
        return "go_to_fixer"

    # --- Assemble StateGraph ---
    workflow = StateGraph(GameState)

    # Add nodes
    workflow.add_node("CEO", ceo_node)
    workflow.add_node("CPO", cpo_node)
    workflow.add_node("Design_Reviewer", design_reviewer_node)
    workflow.add_node("Asset_Gen", asset_node)
    workflow.add_node("Architect", architect_node)
    workflow.add_node("Plan_Reviewer", plan_reviewer_node)
    workflow.add_node("Programmer", programmer_node)
    workflow.add_node("Evaluator", evaluator_node)
    workflow.add_node("Fixer", fixer_node)

    # Set edges
    workflow.add_edge(START, "CEO")
    workflow.add_edge("CEO", "CPO")
    workflow.add_edge("CPO", "Design_Reviewer")

    # Design Loop
    workflow.add_conditional_edges("Design_Reviewer", check_design_loop, {
        "back_to_cpo": "CPO",
        "continue_to_asset": "Asset_Gen"
    })

    workflow.add_edge("Asset_Gen", "Architect")
    workflow.add_edge("Architect", "Plan_Reviewer")

    # Plan Loop
    workflow.add_conditional_edges("Plan_Reviewer", check_plan_loop, {
        "back_to_architect": "Architect",
        "continue_to_programmer": "Programmer"
    })

    workflow.add_edge("Programmer", "Evaluator")

    # Test & Fix Loop
    workflow.add_conditional_edges("Evaluator", check_test_loop, {
        "success": END,
        "failure": END,
        "go_to_fixer": "Fixer"
    })

    workflow.add_edge("Fixer", "Evaluator")

    return workflow.compile()

def run_full_generator_pipeline(user_input, log_callback=print, provider="openai"):
    """
    Executes the full LangGraph pipeline automatically.
    """
    # For other agents
    agents = ArcadeAgentChain(provider, model=None)
    # Specifically for prompt compress agents
    prompt_compress_agents = LocalPromptCompressor(
        provider=config.PROMPT_COMPRESS_PROVIDER,
        model_name=config.PROMPT_COMPRESS_MODEL_NAME,
        temperature=0.1
    )
    output_path = os.path.join(config.OUTPUT_DIR, "generated_game")
    if not os.path.exists(output_path):
        os.makedirs(output_path)

    # 1. Initialize graph
    app_graph = create_game_generator_graph(agents, prompt_compress_agents, log_callback, output_path, provider_name=provider)

    # 2. Prepare initial State
    initial_state = {
        "user_input": user_input,
        "design_iterations": 0,
        "plan_iterations": 0,
        "test_iterations": 0,
        "test_errors": [],
        "project_files": {},
        "is_valid": False,
        "work_dir": output_path
    }

    # 3. Execute graph
    log_callback("[System] Starting LangGraph Multi-Agent Pipeline...")
    final_state = app_graph.invoke(initial_state)

    if final_state["is_valid"]:
        log_callback("[Result] RESULT_SUCCESS: Code passed all validation checks.")
    else:
        log_callback("[Result] RESULT_FAIL: Validation failed. Please review generated files.")

    # try:
    #     img = app_graph.get_graph().draw_mermaid_png()
    #     with open("graph.png", "wb") as f:
    #         f.write(img)
    # except Exception as e:
    #     log_callback(f"[Graph Visualization Error] Could not generate graph image: {str(e)}")

    token_tracker = agents.get_token_tracker()
    log_callback("=" * 50)
    log_callback("[Token Usage Report] Token Cost of Generation and Debug")
    log_callback(f"Prompt Tokens (Input): {token_tracker.prompt_tokens}")
    log_callback(f"Completion Tokens (Output): {token_tracker.completion_tokens}")
    log_callback(f"One Time Max Token Usage (Input + Output): {token_tracker.one_time_token_usage}")
    log_callback(f"Total Tokens (All): {token_tracker.total_tokens}")
    log_callback("=" * 50)


    # Return the final project files dictionary for app.py to process
    return final_state["project_files"]