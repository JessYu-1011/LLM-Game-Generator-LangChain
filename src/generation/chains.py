from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import JsonOutputParser, StrOutputParser
from pydantic import BaseModel, Field
from typing import List

from src.generation.model_factory import get_langchain_model
from src.generation.arcade_tools import ARCADE_LANGCHAIN_TOOLS
from src.prompts.design_prompts import CEO_PROMPT, CPO_PROMPT, CPO_REVIEW_PROMPT
from src.prompts.code_generation_prompts import ARCHITECT_SYSTEM_PROMPT, PROGRAMMER_SYSTEM_PROMPT
from src.prompts.testing_prompts import FIXER_PROMPT, LOGIC_REVIEW_PROMPT, LOGIC_FIXER_PROMPT

class FileSkeleton(BaseModel):
    filename: str = Field(description="The name of the file (e.g., 'main.py')")
    purpose: str = Field(description="Brief explanation of the file's role")
    skeleton_code: str = Field(description="Python skeleton code with class/method definitions and docstrings")


class TechnicalPlan(BaseModel):
    architecture: str = Field(description="Overview of the system architecture")
    files: List[FileSkeleton] = Field(description="List of files to generate")
    constraints: List[str] = Field(description="Critical technical constraints (e.g., 'Check NoneType')")


class ArcadeAgentChain:
    def __init__(self, provider="openai", model="gpt-4o", temperature=0.7):
        self.llm = get_langchain_model(provider, model, temperature)
        self.json_parser = JsonOutputParser(pydantic_object=TechnicalPlan)

    def get_ceo_chain(self):
        prompt = ChatPromptTemplate.from_messages([
            ("system", CEO_PROMPT),
            ("user", "User Idea: {input}\n\nProvide a high-level analysis.")
        ])
        return prompt | self.llm | StrOutputParser()

    def get_cpo_chain(self):
        prompt = ChatPromptTemplate.from_messages([
            ("system", CPO_PROMPT),
            ("user", "User Idea: {idea}\nCEO Analysis: {analysis}\nFeedback: {feedback}")
        ])
        return prompt | self.llm | StrOutputParser()

    def get_reviewer_chain(self):
        prompt = ChatPromptTemplate.from_messages([
            ("system", CPO_REVIEW_PROMPT),
            ("user", "Current GDD:\n{gdd}\n\nProvide feedback.")
        ])
        return prompt | self.llm | StrOutputParser()

    # --- Phase 2: Production Chains (新架構) ---
    def get_architect_chain(self):
        prompt = ChatPromptTemplate.from_messages([
            ("system", ARCHITECT_SYSTEM_PROMPT),
            ("user", "GDD:\n{gdd}\nAssets:\n{assets}\n\nPlan the architecture:\n{format_instructions}")
        ])
        return prompt | self.llm | self.json_parser

    def get_programmer_chain(self):
        llm_with_tools = self.llm.bind_tools(ARCADE_LANGCHAIN_TOOLS)

        prompt = ChatPromptTemplate.from_messages([
            ("system", PROGRAMMER_SYSTEM_PROMPT),
            ("user",
             "Target File: {filename}\n"
             "Purpose: {purpose}\n"
             "Constraints:\n{constraints}\n\n"
             "Skeleton Code:\n{skeleton_code}\n\n"
             "TASK: Implement the full code.\n"
             "CRITICAL RULES:\n"
             "1. Output ONLY valid Python code. NO explanations, NO conversational text.\n"
             "2. Use `arcade.draw_rectangle_filled(center_x, center_y, width, height, color)` for rectangles.\n"
             "3. Do NOT use `arcade.draw_rect_filled` (that is for Arcade 3.0).\n"
             "4. Ensure ALL code is inside a ```python code block.")
        ])
        return prompt | llm_with_tools

    def get_syntax_fixer_chain(self):
        """
        Syntax Fixer Agent:
        當程式碼執行發生 Crash (Runtime Error) 時呼叫。
        專注於修復 Python 語法錯誤、AttributeError (如 NoneType) 或 API 錯誤。
        """
        prompt = ChatPromptTemplate.from_messages([
            ("system", FIXER_PROMPT),
            ("user", "【BROKEN CODE】:\n{code}\n\n【ERROR MESSAGE】:\n{error}\n\n請修復上述錯誤。")
        ])
        return prompt | self.llm | StrOutputParser()

    def get_logic_reviewer_chain(self):
        """
        Logic Reviewer Agent:
        靜態代碼分析，檢查是否使用了 Arcade 3.0 的禁忌語法 (如 draw_rect_filled)
        或遺漏了關鍵檢查 (如 grid None check)。
        """
        prompt = ChatPromptTemplate.from_messages([
            ("system", LOGIC_REVIEW_PROMPT),
            ("user", "【CODE】:\n{code}\n\n請進行邏輯審查。")
        ])
        return prompt | self.llm | StrOutputParser()

    def get_logic_fixer_chain(self):
        """
        Logic Fixer Agent:
        當 Reviewer 發現邏輯問題 (Fail) 時呼叫，負責重寫代碼。
        """
        prompt = ChatPromptTemplate.from_messages([
            ("system", LOGIC_FIXER_PROMPT),
            ("user", "【Error Messages】:\n{error}\n\n【CODE】:\n{code}\n\n請修復上述邏輯問題。")
        ])
        return prompt | self.llm | StrOutputParser()