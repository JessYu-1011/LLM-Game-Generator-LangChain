import functools

from langchain_core.messages import SystemMessage
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import JsonOutputParser, StrOutputParser

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
from src.generation.utils.token_tracker import TokenTrackerCallback
from src.generation.utils.schemas import TechnicalPlan, FixingCodes


def with_llm_injection(provider=None, model=None, temperature=None):
    """
    [Decorator Factory]
    可以在 @with_llm_injection(provider="openai", ...) 這裡帶入參數
    """

    def decorator(func):
        @functools.wraps(func)
        def wrapper(self, *args, **kwargs):
            chain_cfg = getattr(self, 'chain_configs', {}).get(func.__name__, {})

            p = kwargs.pop('provider', chain_cfg.get('provider', provider))
            m = kwargs.pop('model', chain_cfg.get('model', model))
            t = kwargs.pop('temperature', chain_cfg.get('temperature', temperature))

            llm = self._resolve_llm(p, m, t)

            return func(self, llm, *args, **kwargs)

        return wrapper

    return decorator


class ArcadeAgentChain:
    def __init__(self, default_config, chain_configs):
        self.token_tracker = TokenTrackerCallback()
        self.default_config = default_config
        self.chain_configs = chain_configs
        self.llm = self._make_llm(**default_config)
        self.json_parser = JsonOutputParser(pydantic_object=TechnicalPlan)
        self.fixing_codes_parser = JsonOutputParser(pydantic_object=FixingCodes)

    def _make_llm(self, provider, model, temperature):
        llm = get_langchain_model(provider, model, temperature)
        return llm.with_config(callbacks=[self.token_tracker])

    def _resolve_llm(self, p, m, t):
        if p is None and m is None and t is None:
            return self.llm

        return self._make_llm(
            p or self.default_config["provider"],
            m or self.default_config["model"],
            t if t is not None else self.default_config["temperature"]
        )

    # --- Phase 1: Design (CEO/CPO) ---
    @with_llm_injection()
    def get_ceo_chain(self, llm):
        prompt = ChatPromptTemplate.from_messages([
            SystemMessage(content=CEO_PROMPT),
            ("user", "User Idea: {input}\n\nProvide a high-level analysis.")
        ])
        return prompt | llm | StrOutputParser()

    @with_llm_injection()
    def get_cpo_chain(self, llm):
        prompt = ChatPromptTemplate.from_messages([
            SystemMessage(content=CPO_PROMPT),
            ("user", "User Idea: {idea}\nCEO Analysis: {analysis}\nFeedback: {feedback}")
        ])
        return prompt | llm | StrOutputParser()

    @with_llm_injection()
    def get_reviewer_chain(self, llm):
        prompt = ChatPromptTemplate.from_messages([
            SystemMessage(content=CPO_REVIEW_PROMPT),
            ("user", "Current GDD:\n{gdd}\n\n"
                     "Provide feedback to improve this design."
             )
        ])
        return prompt | llm | StrOutputParser()

    # --- Phase 2: Production (Architect & Programmer) ---
    @with_llm_injection()
    def get_architect_chain(self, llm):
        prompt = ChatPromptTemplate.from_messages([
            SystemMessage(content=ARCHITECT_SYSTEM_PROMPT),
            ("user", "GDD:\n{gdd}\n"
                     "Assets:\n{assets}\n\n"
                     "Task: Plan the game architecture. \n"
                     "{format_instructions}"
             )
        ])
        return prompt | llm | self.json_parser

    @with_llm_injection()
    def get_architect_refinement_chain(self, llm):
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
        return prompt | llm | self.json_parser

    @with_llm_injection()
    def get_template_decision_chain(self, llm):
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
        return prompt | llm | StrOutputParser()

    @with_llm_injection()
    def get_plan_reviewer_chain(self, llm):
        prompt = ChatPromptTemplate.from_messages([
            SystemMessage(content=PLAN_REVIEW_PROMPT),
            ("user", "Architecture Plan:\n{plan}\n\n"
                     "Analyze for API correctness and Grid safety."
             )
        ])
        return prompt | llm | StrOutputParser()

    @with_llm_injection()
    def get_programmer_chain(self, llm):
        """
        Generates the code using RAG tools and specific Math Injection.
        """
        llm_with_tools = llm.bind_tools(ARCADE_LANGCHAIN_TOOLS)

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

        return prompt | llm | StrOutputParser()

    # --- Phase 3: Testing & Fixing ---
    @with_llm_injection()
    def get_syntax_fixer_chain(self, llm):
        combined_prompt = f"{FIXER_PROMPT}"
        prompt = ChatPromptTemplate.from_messages([
            SystemMessage(content=combined_prompt),
            ("user", "【BROKEN CODE】:\n{code}\n\n【ERROR MESSAGE】:\n{error}")
        ])
        return prompt | llm | StrOutputParser()

    @with_llm_injection()
    def get_logic_reviewer_chain(self, llm):
        prompt = ChatPromptTemplate.from_messages([
            SystemMessage(content=LOGIC_REVIEW_PROMPT),
            ("user", "【CODE】:\n{code}")
        ])
        return prompt | llm | self.fixing_codes_parser

    @with_llm_injection()
    def get_logic_fixer_chain(self, llm):
        combined_prompt = f"{LOGIC_FIXER_PROMPT}"
        prompt = ChatPromptTemplate.from_messages([
            SystemMessage(content=combined_prompt),
            ("user", "【Error Messages】:\n{error}\n\n【CODE】:\n{code}")
        ])
        return prompt | llm | StrOutputParser()

    @with_llm_injection()
    def get_fuzzer_chain(self, llm):
        """
        [NEW] Generates the Fuzzer Monkey Bot Logic snippet based on the GDD.
        """
        prompt = ChatPromptTemplate.from_messages([
            SystemMessage(content="You are a QA Automation Engineer specializing in Python Arcade 2.x."),
            ("user", FUZZER_GENERATION_PROMPT)
        ])
        return prompt | llm | StrOutputParser()

    def get_token_tracker(self):
        return self.token_tracker