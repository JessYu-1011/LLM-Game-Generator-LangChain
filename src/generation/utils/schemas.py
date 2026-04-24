from pydantic import BaseModel, Field
from typing import List, Optional

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
