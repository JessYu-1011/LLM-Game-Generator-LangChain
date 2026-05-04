import os
import json
import sys
import traceback

from src.generation.asset_gen import generate_assets
from src.generation.core.chains import ArcadeAgentChain
from src.generation.core.game_state import GameState
from src.utils import clean_code_content, save_generated_files
from src.config import config
from src.generation.core.programmer_node_utils import (
    _programmer_node_constraints,
    _programmer_node_choose_templates,
    _programmer_node_templates_inject_prompts,
    _programmer_node_math_injection, _programmer_node_extract_safe_constants,
    _programmer_node_generate_images_from_code, _programmer_node_apply_import_failsafe
)

def ceo_node(state: GameState, agents: ArcadeAgentChain, log_callback):
    log_callback(f"[Design] CEO Analyzing idea: {state['user_input']}...")
    token_tracker = agents.get_token_tracker()
    with token_tracker.track_step("ceo"):
        analysis = agents.get_ceo_chain().invoke({"input": state["user_input"]})
    return {"ceo_analysis": analysis, "design_iterations": 0, "design_feedback": "None"}

def cpo_node(state: GameState, agents: ArcadeAgentChain, log_callback):
    log_callback(f"[Design] CPO Drafting GDD (Round {state['design_iterations'] + 1})...")
    token_tracker = agents.get_token_tracker()
    with token_tracker.track_step("cpo"):
        gdd = agents.get_cpo_chain().invoke({
            "idea": state["user_input"],
            "analysis": state["ceo_analysis"],
            "feedback": state["design_feedback"]
        })
    return {"gdd": gdd}

def design_reviewer_node(state: GameState, agents: ArcadeAgentChain, log_callback):
    log_callback("[Design] Reviewer critiquing GDD...")
    token_tracker = agents.get_token_tracker()
    with token_tracker.track_step("design"):
        feedback = agents.get_reviewer_chain().invoke({"gdd": state["gdd"]})
    return {
        "design_feedback": feedback,
        "design_iterations": state["design_iterations"] + 1
    }

def asset_node(state: GameState, agents: ArcadeAgentChain, log_callback):
    log_callback("[System] Generating Assets...")
    token_tracker = agents.get_token_tracker()
    with token_tracker.track_step("asset"):
        response = agents.get_asset_chain().invoke({"gdd": state["gdd"]})
    assets = generate_assets(response, log_callback)
    return {"assets_json": assets}

def architect_node(state: GameState, agents: ArcadeAgentChain, log_callback):
    log_callback(f"[Architect] Planning system architecture (Round {state['plan_iterations'] + 1})...")
    token_tracker = agents.get_token_tracker()
    if state['plan_iterations'] == 0:
        with token_tracker.track_step("architect"):
            plan = agents.get_architect_chain().invoke({
                "gdd": state["gdd"],
                "assets": state["assets_json"],
                "format_instructions": agents.json_parser.get_format_instructions()
            })
    else:
        log_callback("[Architect] Refining plan based on feedback...")
        plan_str = json.dumps(state["architecture_plan"], indent=2)
        with token_tracker.track_step("architect_refinement"):
            plan = agents.get_architect_refinement_chain().invoke({
                "original_plan": plan_str,
                "feedback": state["plan_feedback"],
                "format_instructions": agents.json_parser.get_format_instructions()
            })
    return {"architecture_plan": plan}

def plan_reviewer_node(state: GameState, agents: ArcadeAgentChain, log_callback):
    log_callback("[Architect] Plan Review...")
    plan_str = json.dumps(state["architecture_plan"], indent=2)
    token_tracker = agents.get_token_tracker()
    with token_tracker.track_step("architect_plan_review"):
        feedback = agents.get_plan_reviewer_chain().invoke({"plan": plan_str})
    return {
        "plan_feedback": feedback,
        "plan_iterations": state["plan_iterations"] + 1
    }

def programmer_node(state: GameState, agents: ArcadeAgentChain, prompt_compress_agents, log_callback, work_dir):
    math_injection = _programmer_node_math_injection(state, log_callback)

    needed_templates = _programmer_node_choose_templates(state, agents, prompt_compress_agents, log_callback)

    [template_code_blocks,
     guaranteed_imports ,
     template_injection_prompt] = _programmer_node_templates_inject_prompts(needed_templates, log_callback)

    full_constraints = _programmer_node_constraints(state, log_callback)

    """
    ================== Generating codes ==========================
    """
    
    token_tracker = agents.get_token_tracker()
    with token_tracker.track_step("programmer"):
        response = agents.get_programmer_chain().invoke({
            "architecture_plan": state["architecture_plan"],
            "review_feedback": state["plan_feedback"],
            "constraints": full_constraints,
            "math_context": math_injection,
            "templates": template_injection_prompt,
        })

    content = response.content if hasattr(response, 'content') else str(response)
    cleaned_code = clean_code_content(content)

    if config.USING_PICTURE_GENERATE:
        safe_env = _programmer_node_extract_safe_constants(cleaned_code)
        _programmer_node_generate_images_from_code(cleaned_code, safe_env, log_callback)

    cleaned_code = _programmer_node_apply_import_failsafe(cleaned_code, guaranteed_imports, log_callback)

    log_callback("[Programmer] [Test] Generating Fuzzer logic snippet...")
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

def evaluator_node(state: GameState, agents: ArcadeAgentChain, log_callback, work_dir):
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
    token_tracker = agents.get_token_tracker()
    with token_tracker.track_step("evaluator"):
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
        return {"test_errors": state.get("test_errors", []) + [error_msg]}
    else:
        log_callback("[Review] Strict API validation passed.")

    log_callback("[Result] Code passed ALL validations successfully!")
    return {"is_valid": True}

def fixer_node(state: GameState, agents: ArcadeAgentChain, prompt_compress_agents, log_callback, work_dir):
    log_callback("[Fixer] Reading historical error logs and attempting fix...")
    latest_error = state["test_errors"][-1]

    history_errors = state["test_errors"][:-1]
    error_prompt = latest_error
    if history_errors:
        chain = prompt_compress_agents.get_compress_errors_chain()
        if chain is not None:
            token_tracker = agents.get_token_tracker()
            with token_tracker.track_step("compress_errors"):
                compressed_history = chain.invoke({"errors": history_errors})
            error_prompt = f"[Past Failed Attempts (Do NOT repeat these mistakes)]:\n{compressed_history}\n\n[Latest Error]:\n{latest_error}"
            # error_prompt = f"[Past Failed Attempts (Do NOT repeat these mistakes)]:\n{history_errors}\n\n[Latest Error]:\n{latest_error}"

    token_tracker = agents.get_token_tracker()

    if "[LogicError]" in latest_error:
        with token_tracker.track_step("logic_fixer"):
            response = agents.get_logic_fixer_chain().invoke({
                "code": state["current_code"],
                "error": error_prompt,
                "gdd": state["gdd"]
            })
    else:
        with token_tracker.track_step("syntax_fixer"):
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