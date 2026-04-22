from typing import TypedDict, Annotated, List, Dict, Any
import operator

class GameState(TypedDict):
    user_input: str

    # Design Phase
    ceo_analysis: str
    gdd: str
    design_feedback: str
    design_iterations: int

    # Asset Phase
    assets_json: str

    # Plan Phase
    architecture_plan: dict
    plan_feedback: str
    plan_iterations: int

    # Production Phase
    math_context: str
    project_files: Dict[str, str]
    current_code: str

    # Test & Fix Phase (Memory Mechanism)
    # operator.add ensures new errors are appended to the list, not overwritten
    test_errors: Annotated[List[str], operator.add]
    test_iterations: int
    is_valid: bool
    work_dir: str