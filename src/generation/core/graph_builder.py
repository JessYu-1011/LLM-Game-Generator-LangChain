from functools import partial
from langgraph.graph import StateGraph, START, END

from src.generation.core.game_state import GameState
from src.generation.core.nodes import (
    ceo_node, cpo_node, design_reviewer_node, asset_node,
    architect_node, plan_reviewer_node,
    programmer_node, evaluator_node, fixer_node,
    check_design_loop, check_plan_loop, check_test_loop
)


def create_game_generator_graph(agents, prompt_compress_agents, log_callback, work_dir, provider_name="openai"):
    """
    Creates and returns a compiled LangGraph application using partial injection.
    """
    workflow = StateGraph(GameState)

    workflow.add_node("CEO", partial(ceo_node, agents=agents, log_callback=log_callback))
    workflow.add_node("CPO", partial(cpo_node, agents=agents, log_callback=log_callback))
    workflow.add_node("Design_Reviewer", partial(design_reviewer_node, agents=agents, log_callback=log_callback))
    workflow.add_node("Asset_Gen", partial(asset_node, log_callback=log_callback, provider_name=provider_name))
    workflow.add_node("Architect", partial(architect_node, agents=agents, log_callback=log_callback))
    workflow.add_node("Plan_Reviewer", partial(plan_reviewer_node, agents=agents, log_callback=log_callback))

    workflow.add_node("Programmer", partial(
        programmer_node,
        agents=agents,
        prompt_compress_agents=prompt_compress_agents,
        log_callback=log_callback,
        work_dir=work_dir
    ))
    workflow.add_node("Evaluator", partial(evaluator_node, agents=agents, log_callback=log_callback, work_dir=work_dir))
    workflow.add_node("Fixer", partial(
        fixer_node,
        agents=agents,
        prompt_compress_agents=prompt_compress_agents,
        log_callback=log_callback,
        work_dir=work_dir
    ))

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