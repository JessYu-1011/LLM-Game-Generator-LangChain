import os
from src.generation.chains import ArcadeAgentChain
from src.utils import clean_code_content


def run_design_phase(user_input, log_callback=print, provider="openai", model="gpt-4o"):
    """
    執行設計階段：CEO -> CPO -> Reviewer 循環
    """
    agents = ArcadeAgentChain(provider, model)

    log_callback(f"[Design] CEO Analyzing idea: {user_input}...")
    ceo_analysis = agents.get_ceo_chain().invoke({"input": user_input})

    # CPO & Reviewer Loop
    feedback = "None"
    final_gdd = ""

    log_callback("[Design] CPO Drafting GDD...")
    # Review for 2 times
    for i in range(2):
        final_gdd = agents.get_cpo_chain().invoke({
            "idea": user_input,
            "analysis": ceo_analysis,
            "feedback": feedback
        })

        log_callback(f"[Design] Reviewer critiquing round {i + 1}...")
        feedback = agents.get_reviewer_chain().invoke({"gdd": final_gdd})

    return final_gdd


def run_production_pipeline(gdd_context, asset_json, log_callback=print, provider="openai", model=None):
    """
    執行生產階段，強制產出單一 game.py 檔案。
    """
    agents = ArcadeAgentChain(provider, model)

    # 1. 獲取架構計畫
    log_callback("[Architect] 規劃系統架構...")
    plan = agents.get_architect_chain().invoke({
        "gdd": gdd_context,
        "assets": asset_json,
        "format_instructions": agents.json_parser.get_format_instructions()
    })

    # 2. 強制單一檔案生成 (game.py)
    log_callback("[Programmer] 正在實作 game.py (整合所有邏輯)...")
    response = agents.get_programmer_chain().invoke({
        "architecture_plan": plan.get('architecture', ''),
        "constraints": "\n".join(plan.get('constraints', []))
    })

    # 獲取內容並進行代碼清洗 (移除解釋性文字)
    content = response.content if hasattr(response, 'content') else str(response)
    cleaned_code = clean_code_content(content)

    # 只回傳一個檔案
    return {"game.py": cleaned_code}

def run_test_and_fix_phase(project_files, work_dir, log_callback=print, provider="openai", model="gpt-4o"):
    """
    [NEW] 執行測試與修復階段：
    1. 寫入檔案 (Fuzzer 需要實體檔案)
    2. Fuzzer Loop (Runtime Fixer)
    3. Logic Loop (Static Analysis Fixer)
    """
    agents = ArcadeAgentChain(provider, model)

    # 0. Ensure the file has been written to disk for the Fuzzer to run
    if not os.path.exists(work_dir):
        os.makedirs(work_dir)

    for filename, content in project_files.items():
        file_path = os.path.join(work_dir, filename)
        with open(file_path, "w", encoding="utf-8") as f:
            f.write(content)

    main_file = os.path.join(work_dir, "main.py")
    if not os.path.exists(main_file):
        log_callback("[Test] ⚠️ main.py not found. Skipping tests.")
        return project_files

    # 1. Runtime Fuzzing & Syntax Fixer Loop
    max_retries = 3
    for attempt in range(max_retries):
        log_callback(f"[Test] 🧪 Running Fuzzer (Attempt {attempt + 1}/{max_retries})...")

        # Dynamically import the runner to avoid circular imports and only require it when testing
        try:
            from src.testing.runner import run_fuzz_test
        except ImportError:
            log_callback("[Test] ⚠️ Runner not found. Skipping Fuzz test.")
            break

        success, error_msg = run_fuzz_test(main_file, duration=5)

        if success:
            log_callback("[Test] ✅ Fuzzer Passed (Runtime Safe).")
            break

        log_callback(f"[Test] ❌ Runtime Crash Detected:\n{error_msg}")
        log_callback("[Fixer] 🔧 Engaging Syntax Fixer...")

        # Read the broken code for the fixer
        with open(main_file, "r", encoding="utf-8") as f:
            broken_code = f.read()

        # 呼叫 Syntax Fixer Chain
        fixer_chain = agents.get_syntax_fixer_chain()
        fixed_code = fixer_chain.invoke({
            "code": broken_code,
            "error": error_msg
        })

        # 清理並儲存
        fixed_code = fixed_code.replace("```python", "").replace("```", "").strip()
        with open(main_file, "w", encoding="utf-8") as f:
            f.write(fixed_code)

        project_files["main.py"] = fixed_code
        log_callback("[Fixer] ✅ Code patched and saved.")

    # 2. Static Logic Review & Fixer Loop
    log_callback("[Review] 🧐 Running Static Logic Analysis...")
    reviewer_chain = agents.get_logic_reviewer_chain()
    fixer_chain = agents.get_logic_fixer_chain()

    # 針對主要邏輯檔案進行檢查
    target_files = ["main.py", "logic.py"]
    for filename in target_files:
        if filename not in project_files:
            continue

        code = project_files[filename]
        review_result = reviewer_chain.invoke({"code": code})

        # 如果 Reviewer 回傳 FAIL
        if "FAIL" in review_result:
            log_callback(f"[Review] ⚠️ Logic Issue in {filename}: {review_result}")
            log_callback(f"[Fixer] 🧠 Fixing Logic in {filename}...")

            fixed_code = fixer_chain.invoke({
                "code": code,
                "error": review_result
            })

            fixed_code = fixed_code.replace("```python", "").replace("```", "").strip()

            # 寫回檔案與更新字典
            with open(os.path.join(work_dir, filename), "w", encoding="utf-8") as f:
                f.write(fixed_code)
            project_files[filename] = fixed_code

            log_callback(f"[Fixer] ✅ {filename} logic patched.")
        else:
            log_callback(f"[Review] ✅ {filename} passed logic check.")

    return project_files