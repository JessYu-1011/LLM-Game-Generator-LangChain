from langchain_core.messages import SystemMessage
from langchain_core.output_parsers import StrOutputParser
from langchain_core.prompts import ChatPromptTemplate

from src.generation.model_factory import get_langchain_model


class LocalPromptCompressor:
    def __init__(self, token_tracker, provider="ollama", model_name="llama3.1:latest", temperature: float = 0.1, log_callback=print):
        """
        Use local models for compressing the prompts
        """
        self.token_tracker = token_tracker
        self.local_llm = get_langchain_model(provider=provider, model_name=model_name, temperature=temperature)
        self.local_llm = self.local_llm.with_config(callbacks=[token_tracker])
        self.log_callback = log_callback

    def get_compress_errors_chain(self):
        """
        To compress the history errors.
        """
        try:
            prompt = ChatPromptTemplate.from_messages([
                SystemMessage(content="""
                   You are a python error summarization assistant.\n\n
                   Your task is to take verbose Python error messages and summarize them into concise, actionable insights that retain all critical information for debugging.\n\n
                   Make sure that you do NOT lose any important technical details, constraints, or instructions in the summarization process.\n\n
                   """),
                ("user",
                 "Summarize the following Python error message into a concise format suitable for debugging:\n\n{errors}")
            ])
            return prompt | self.local_llm | StrOutputParser()
        except ConnectionError:
            self.log_callback("The Ollama server for prompt compression hasn't started. Make sure that the server is running.")
            return None

    def get_gdd_mechanics_extractor(self):
        prompt = ""
        try:
            prompt = ChatPromptTemplate.from_messages([
                SystemMessage(
                    content="You are a technical extractor. Extract ONLY the core gameplay mechanics, controls, and win/loss conditions from the GDD.\n\n"
                            "Discard all story, visual, and audio descriptions. Be extremely concise."),
                ("user", "GDD:\n{gdd}")
            ])
        except ConnectionError:
            self.log_callback("The Ollama server for prompt compression hasn't started. Make sure that the server is running.")
        return prompt | self.local_llm | StrOutputParser()