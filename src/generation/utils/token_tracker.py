from langchain_core.callbacks import BaseCallbackHandler
import contextlib


class TokenTrackerCallback(BaseCallbackHandler):
    def __init__(self):
        # 總體統計
        self.prompt_tokens = 0
        self.completion_tokens = 0
        self.one_time_token_usage = 0

        # 分組 (Agent/Step) 統計
        self.step_usage = {}
        self._current_step = "System"  # 預設標籤

    @property
    def total_tokens(self):
        return self.prompt_tokens + self.completion_tokens

    @property
    def one_time_max_token_usage(self):
        return self.one_time_token_usage

    @contextlib.contextmanager
    def track_step(self, step_name: str):
        """
        Context manager (上下文管理器)。
        用來優雅地切換當前正在追蹤的 Agent 名稱。
        """
        previous_step = self._current_step
        self._current_step = step_name

        # 初始化該步驟的統計字典
        if step_name not in self.step_usage:
            self.step_usage[step_name] = {
                "prompt": 0,
                "completion": 0,
                "total": 0,
                "max_single": 0
            }
        try:
            yield
        finally:
            # 執行完畢後切回原本的步驟
            self._current_step = previous_step

    def set_current_step(self, step_name: str):
        """簡單的 Setter，如果你不想用 with 語句，可以直接呼叫這個來切換"""
        self._current_step = step_name
        if step_name not in self.step_usage:
            self.step_usage[step_name] = {
                "prompt": 0, "completion": 0, "total": 0, "max_single": 0
            }

    def on_llm_end(self, response, **kwargs):
        counted = False
        prompt_tokens = 0
        completion_tokens = 0

        if response.generations:
            for gen_list in response.generations:
                for gen in gen_list:
                    if (hasattr(gen, "message") and
                            hasattr(gen.message, "usage_metadata") and
                            gen.message.usage_metadata):
                        usage = gen.message.usage_metadata
                        prompt_tokens += usage.get("input_tokens", 0)
                        completion_tokens += usage.get("output_tokens", 0)
                        counted = True

        if (not counted and
                response.llm_output and
                "token_usage" in response.llm_output):
            usage = response.llm_output["token_usage"]
            prompt_tokens += usage.get("prompt_tokens", 0)
            completion_tokens += usage.get("completion_tokens", 0)

        current_total = prompt_tokens + completion_tokens

        # --- 1. 更新總體統計 ---
        if self.one_time_token_usage < current_total:
            self.one_time_token_usage = current_total

        self.prompt_tokens += prompt_tokens
        self.completion_tokens += completion_tokens

        # --- 2. 更新當前 Agent (Step) 統計 ---
        # 防呆，確保字典已被初始化
        if self._current_step not in self.step_usage:
            self.step_usage[self._current_step] = {"prompt": 0, "completion": 0, "total": 0, "max_single": 0}

        stats = self.step_usage[self._current_step]
        stats["prompt"] += prompt_tokens
        stats["completion"] += completion_tokens
        stats["total"] += current_total
        if stats["max_single"] < current_total:
            stats["max_single"] = current_total

    def print_summary(self, log_callback = print):
        """印出詳細的 Token 使用報告"""
        log_callback("\n" + "=" * 50)
        log_callback("[Token Usage Report] Breakdown by Agent")
        log_callback("=" * 50)

        # 依序印出每個 Agent 的花費
        for step, stats in self.step_usage.items():
            if stats["total"] > 0:  # 只印出有實際消耗的 Agent
                log_callback(f"[{step.upper()}]")
                log_callback(f"  Prompt (Input) : {stats['prompt']:>7}")
                log_callback(f"  Completion     : {stats['completion']:>7}")
                log_callback(f"  Total Tokens   : {stats['total']:>7}")
                log_callback(f"  Max Single     : {stats['max_single']:>7}")
                log_callback("-" * 50)

        log_callback("[OVERALL SYSTEM]")
        log_callback(f"  Total Prompt   : {self.prompt_tokens:>7}")
        log_callback(f"  Total Output   : {self.completion_tokens:>7}")
        log_callback(f"  GRAND TOTAL    : {self.total_tokens:>7}")
        log_callback(f"  Sys Max Single : {self.one_time_max_token_usage:>7}")
        log_callback("=" * 50 + "\n")