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

    # --- Phase 1: Design ---
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

    # --- Phase 2: Production ---
    def get_architect_chain(self):
        # 這裡依然讓它生成 TechnicalPlan，保留多檔案擴充性
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
             "Architecture Context:\n{architecture_plan}\n\n"
             "Target File: game.py\n" # 改為 game.py
             "Constraints:\n{constraints}\n\n"
             "TASK: Implement the FULL game logic in this SINGLE file (game.py).\n"
             "CRITICAL RULES:\n"
             "1. Combine all planned classes and logic from the architecture into game.py.\n"
             "2. Output ONLY valid Python code. NO explanations, NO conversational text.\n"
             "3. Use `arcade.draw_rectangle_filled(center_x, center_y, width, height, color)` for rectangles.\n"
             "4. Do NOT use `arcade.draw_rect_filled` (that is for Arcade 3.0).\n"
             "5. Ensure ALL code is inside a SINGLE ```python code block.")
        ])
        return prompt | llm_with_tools

    # --- Phase 3: Testing & Fixing ---
    def get_syntax_fixer_chain(self):
        prompt = ChatPromptTemplate.from_messages([
            ("system", FIXER_PROMPT),
            ("user", "【BROKEN CODE】:\n{code}\n\n【ERROR MESSAGE】:\n{error}\n\n請修復上述錯誤並回傳完整代碼。")
        ])
        return prompt | self.llm | StrOutputParser()

    def get_logic_reviewer_chain(self):
        prompt = ChatPromptTemplate.from_messages([
            ("system", LOGIC_REVIEW_PROMPT),
            ("user", "【CODE】:\n{code}\n\n請根據 Arcade 2.x 規範進行邏輯審查。")
        ])
        return prompt | self.llm | StrOutputParser()

    def get_logic_fixer_chain(self):
        prompt = ChatPromptTemplate.from_messages([
            ("system", LOGIC_FIXER_PROMPT),
            ("user", "【Error Messages】:\n{error}\n\n【CODE】:\n{code}\n\n請修復邏輯問題並回傳完整代碼。")
        ])
        return prompt | self.llm | StrOutputParser()