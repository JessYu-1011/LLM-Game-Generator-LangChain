import os
from src.config import config
from generation.core.chains import ArcadeAgentChain
from generation.utils.prompt_compress_node import LocalPromptCompressor
from src.generation.core.graph_builder import create_game_generator_graph


def run_full_generator_pipeline(user_input, log_callback=print, provider="openai"):
    """
    Executes the full LangGraph pipeline automatically.
    """
    # Agents
    agents = ArcadeAgentChain(provider, model=None)
    prompt_compress_agents = LocalPromptCompressor(
        provider=config.PROMPT_COMPRESS_PROVIDER,
        model_name=config.PROMPT_COMPRESS_MODEL_NAME,
        temperature=0.1
    )

    # Output dir
    output_path = os.path.join(config.OUTPUT_DIR, "generated_game")
    if not os.path.exists(output_path):
        os.makedirs(output_path)

    # Initialize graph
    app_graph = create_game_generator_graph(
        agents=agents,
        prompt_compress_agents=prompt_compress_agents,
        log_callback=log_callback,
        work_dir=output_path,
        provider_name=provider
    )

    # Initial state
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

    log_callback("[System] Starting LangGraph Multi-Agent Pipeline...")
    final_state = app_graph.invoke(initial_state)

    if final_state.get("is_valid"):
        log_callback("[Result] RESULT_SUCCESS: Code passed all validation checks.")
    else:
        log_callback("[Result] RESULT_FAIL: Validation failed. Please review generated files.")

    # Token calculation
    token_tracker = agents.get_token_tracker()
    log_callback("=" * 50)
    log_callback("[Token Usage Report] Token Cost of Generation and Debug")
    log_callback(f"Prompt Tokens (Input): {token_tracker.prompt_tokens}")
    log_callback(f"Completion Tokens (Output): {token_tracker.completion_tokens}")
    log_callback(f"One Time Max Token Usage: {token_tracker.one_time_token_usage}")
    log_callback(f"Total Tokens (All): {token_tracker.total_tokens}")
    log_callback("=" * 50)

    # Return the final project files dictionary
    return final_state.get("project_files", {})