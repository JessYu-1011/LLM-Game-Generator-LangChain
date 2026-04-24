from langchain_core.callbacks import BaseCallbackHandler

class TokenTrackerCallback(BaseCallbackHandler):
    def __init__(self):
        self.prompt_tokens = 0
        self.completion_tokens = 0
        self.one_time_token_usage = 0

    @property
    def total_tokens(self):
        return self.prompt_tokens + self.completion_tokens

    @property
    def one_time_max_token_usage(self):
        return self.one_time_token_usage

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
                        prompt_tokens = usage.get("input_tokens", 0)
                        completion_tokens = usage.get("output_tokens", 0)
                        if self.one_time_token_usage < (prompt_tokens + completion_tokens):
                            self.one_time_token_usage = prompt_tokens + completion_tokens

                        counted = True

        if (not counted and
            response.llm_output and
            "token_usage" in response.llm_output):

            usage = response.llm_output["token_usage"]
            prompt_tokens = usage.get("prompt_tokens", 0)
            completion_tokens = usage.get("completion_tokens", 0)
            if self.one_time_token_usage < (prompt_tokens + completion_tokens):
                self.one_time_token_usage = prompt_tokens + completion_tokens

        self.prompt_tokens += prompt_tokens
        self.completion_tokens += completion_tokens