from langchain_core.messages import SystemMessage
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import JsonOutputParser, StrOutputParser
from langchain_core.callbacks import BaseCallbackHandler
from pydantic import BaseModel, Field
from typing import List, Optional

from src.generation.model_factory import get_langchain_model
from src.generation.arcade_tools import ARCADE_LANGCHAIN_TOOLS
from src.prompts.code_generation_prompts import (
    ARCHITECT_SYSTEM_PROMPT,
    PROGRAMMER_PROMPT_TEMPLATE,
    PLAN_REVIEW_PROMPT,
    FUZZER_GENERATION_PROMPT
)
from src.prompts.design_prompts import CEO_PROMPT, CPO_PROMPT, CPO_REVIEW_PROMPT
from src.prompts.testing_prompts import FIXER_PROMPT, LOGIC_REVIEW_PROMPT, LOGIC_FIXER_PROMPT


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
                    if hasattr(gen, "message") and hasattr(gen.message,
                                                           "usage_metadata") and gen.message.usage_metadata:
                        usage = gen.message.usage_metadata
                        prompt_tokens = usage.get("input_tokens", 0)
                        completion_tokens = usage.get("output_tokens", 0)
                        if self.one_time_token_usage < (prompt_tokens + completion_tokens):
                            self.one_time_token_usage = prompt_tokens + completion_tokens

                        counted = True

        if not counted and response.llm_output and "token_usage" in response.llm_output:
            usage = response.llm_output["token_usage"]
            prompt_tokens = usage.get("prompt_tokens", 0)
            completion_tokens = usage.get("completion_tokens", 0)
            if self.one_time_token_usage < (prompt_tokens + completion_tokens):
                self.one_time_token_usage = prompt_tokens + completion_tokens

        self.prompt_tokens += prompt_tokens
        self.completion_tokens += completion_tokens


class TechnicalPlan(BaseModel):
    architecture: str = Field(description="Overview of the system architecture")
    constraints: List[str] = Field(description="Critical technical constraints (e.g., 'Check NoneType')")

class FixingCodes(BaseModel):
    status: str = Field(description="Whether the logic review is pass")
    start_line: Optional[int] = Field(
        default=None,
        description="Start line of the code that needs to be fixed in the original file."
    )
    end_line: Optional[int] = Field(
        default=None,
        description="End line of the code that needs to be fixed in the original file."
    )
    codes_to_replace: Optional[str] = Field(
        default=None,
        description=(
            "The fully corrected Python code snippet to replace the lines from start_line to end_line. "
            "CRITICAL: The output MUST be strictly enclosed in markdown code blocks like ```python= ... ```. "
            "It MUST adhere completely to Arcade 2.6.x standard (e.g., use 'arcade.draw_rectangle_filled' and 'arcade.start_render()', "
            "NEVER use Arcade 3.0 APIs like 'draw_rect_filled')."
        )
    )


class ArcadeAgentChain:
    def __init__(self, provider="openai", model=None, temperature=0.7):
        self.token_tracker = TokenTrackerCallback()
        self.llm = get_langchain_model(provider, model, temperature)
        self.llm = self.llm.with_config(callbacks=[self.token_tracker])
        self.json_parser = JsonOutputParser(pydantic_object=TechnicalPlan)
        self.fixing_codes_parser = JsonOutputParser(pydantic_object=FixingCodes)

    # --- Phase 1: Design (CEO/CPO) ---
    def get_ceo_chain(self):
        prompt = ChatPromptTemplate.from_messages([
            SystemMessage(content=CEO_PROMPT),
            ("user", "User Idea: {input}\n\nProvide a high-level analysis.")
        ])
        return prompt | self.llm | StrOutputParser()

    def get_cpo_chain(self):
        prompt = ChatPromptTemplate.from_messages([
            SystemMessage(content=CPO_PROMPT),
            ("user", "User Idea: {idea}\nCEO Analysis: {analysis}\nFeedback: {feedback}")
        ])
        return prompt | self.llm | StrOutputParser()

    def get_reviewer_chain(self):
        prompt = ChatPromptTemplate.from_messages([
            SystemMessage(content=CPO_REVIEW_PROMPT),
            ("user", "Current GDD:\n{gdd}\n\n"
                     "Provide feedback to improve this design."
            )
        ])
        return prompt | self.llm | StrOutputParser()

    # --- Phase 2: Production (Architect & Programmer) ---
    def get_architect_chain(self):
        prompt = ChatPromptTemplate.from_messages([
            SystemMessage(content=ARCHITECT_SYSTEM_PROMPT),
            ("user", "GDD:\n{gdd}\n"
                     "Assets:\n{assets}\n\n"
                     "Task: Plan the game architecture. \n"
                     "{format_instructions}"
            )
        ])
        return prompt | self.llm | self.json_parser

    def get_architect_refinement_chain(self):
        """
        [NEW] Refines the Technical Plan based on Reviewer feedback.
        Matches the logic: 'Rewrite the Technical Implementation Plan by incorporating the feedback.'
        """
        prompt = ChatPromptTemplate.from_messages([
            SystemMessage(content=ARCHITECT_SYSTEM_PROMPT),
            ("user",
             "Original Plan JSON:\n{original_plan}\n\n"
             "Reviewer Feedback:\n{feedback}\n\n"
             "TASK: Refine the architecture JSON to address the feedback.\n"
             "{format_instructions}")
        ])
        return prompt | self.llm | self.json_parser

    def get_template_decision_chain(self):
        """
        [NEW] Chain to decide which pre-built templates to inject into the game code.
        """
        prompt = ChatPromptTemplate.from_messages([
            SystemMessage(content="You are a technical software architect specializing in the Arcade framework."),
            ("user",
             "Analyze this Game Design Document (GDD) and decide which Python template modules are needed for the game.\n"
             "Available templates:\n"
             "**Important**: You must use `asset_manager.py` under any circumstances."
             "- \"menu.py\": Provides `PauseView` and `SettingsView` (Arcade GUI) for pause menu and volume control.\n"
             "- \"camera.py\": Provides `FollowCamera` for 2D scrolling if the game world/map is larger than the screen.\n"
             "- \"asset_manager.py\": Provides `AssetManager` for safely loading images and sounds. ALWAYS recommend this if game has graphics.\n\n"
             "GDD:\n{gdd}\n\n"
             "Return ONLY a JSON list of filenames. Example: [\"menu.py\", \"asset_manager.py\"]")
        ])
        return prompt | self.llm | StrOutputParser()

    def get_plan_reviewer_chain(self):
        prompt = ChatPromptTemplate.from_messages([
            SystemMessage(content=PLAN_REVIEW_PROMPT),
            ("user", "Architecture Plan:\n{plan}\n\n"
                     "Analyze for API correctness and Grid safety."
            )
        ])
        return prompt | self.llm | StrOutputParser()

    def get_programmer_chain(self):
        """
        Generates the code using RAG tools and specific Math Injection.
        """
        llm_with_tools = self.llm.bind_tools(ARCADE_LANGCHAIN_TOOLS)

        combined_system = f"{PROGRAMMER_PROMPT_TEMPLATE}"

        legacy_conventions = """
    ARCADE 2.x (LEGACY) MANDATORY CONVENTIONS:
    1. Drawing: Use 'draw_rectangle_filled' (center_x, center_y, width, height, color). 
       DO NOT use Arcade 3.0 'draw_rect_filled' or XYWH objects.
    2. Rendering: You MUST call 'arcade.start_render()' as the first line in 'on_draw'.
    3. Textures: The 'arcade.Texture(name, image)' constructor REQUIRES a unique name string as the first argument.
    4. Sprite Update: The 'update()' method for Sprites typically takes NO arguments. 
       Do NOT include 'delta_time' in Sprite.update unless manually passed.
    5. Grid Safety: Always verify 'if grid[r][c] is not None:' before accessing its attributes.
    """

        prompt = ChatPromptTemplate.from_messages([
            SystemMessage(content=combined_system),
            ("user",
             "Architecture Context:\n{architecture_plan}\n\n"
             "Review Feedback:\n{review_feedback}\n\n"
             "Technical Constraints:\n{constraints}\n\n"
             f"RULES & HELPERS:\n{legacy_conventions}\n\n"
             "Math & Physics Formulas (MANDATORY):\n{math_context}\n\n"
             "TASK: Implement the FULL game logic in 'game.py'.\n"
             "Templates: \n {templates}"
             "Output ONLY the code block.")
        ])

        return prompt | self.llm | StrOutputParser()

    # --- Phase 3: Testing & Fixing ---
    def get_syntax_fixer_chain(self):
        combined_prompt = f"{FIXER_PROMPT}"
        prompt = ChatPromptTemplate.from_messages([
            SystemMessage(content=combined_prompt),
            ("user", "【BROKEN CODE】:\n{code}\n\n【ERROR MESSAGE】:\n{error}")
        ])
        return prompt | self.llm | StrOutputParser()

    def get_logic_reviewer_chain(self):
        prompt = ChatPromptTemplate.from_messages([
            SystemMessage(content=LOGIC_REVIEW_PROMPT),
            ("user", "【CODE】:\n{code}")
        ])
        return prompt | self.llm | self.fixing_codes_parser

    def get_logic_fixer_chain(self):
        combined_prompt = f"{LOGIC_FIXER_PROMPT}"
        prompt = ChatPromptTemplate.from_messages([
            SystemMessage(content=combined_prompt),
            ("user", "【Error Messages】:\n{error}\n\n【CODE】:\n{code}")
        ])
        return prompt | self.llm | StrOutputParser()

    def get_fuzzer_chain(self):
        """
        [NEW] Generates the Fuzzer Monkey Bot Logic snippet based on the GDD.
        """
        prompt = ChatPromptTemplate.from_messages([
            SystemMessage(content="You are a QA Automation Engineer specializing in Python Arcade 2.x."),
            ("user", FUZZER_GENERATION_PROMPT)
        ])
        return prompt | self.llm | StrOutputParser()

    def get_token_tracker(self):
        return self.token_tracker