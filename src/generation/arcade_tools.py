from langchain_core.tools import tool
from src.rag_service.rag import rag_instance

@tool
def get_arcade_2_x_api_conventions() -> str:
    """
    Get mandatory API mapping rules and legacy argument signatures for Arcade 2.x.
    Call this when you need to verify drawing functions, rendering pipelines, or texture handling.
    """
    return """
    ARCADE 2.x (LEGACY) MANDATORY CONVENTIONS:
    1. Drawing: Use 'draw_rectangle_filled' (center_x, center_y, width, height, color). 
       DO NOT use Arcade 3.0 'draw_rect_filled' or XYWH objects.
    2. Rendering: You MUST call 'arcade.start_render()' as the first line in 'on_draw'.
    3. Textures: The 'arcade.Texture(name, image)' constructor REQUIRES a unique name string as the first argument.
    4. Sprite Update: The 'update()' method for Sprites typically takes NO arguments. 
       Do NOT include 'delta_time' in Sprite.update unless manually passed.
    5. Grid Safety: Always verify 'if grid[r][c] is not None:' before accessing its attributes.
    """

@tool
def search_arcade_kb(query: str) -> str:
    """
    Search the Arcade 2.6.x knowledge base for specific implementation details,
    code examples, or logic patterns (e.g., collision, movement, grid management).
    """
    return rag_instance.query(query, n_results=1)

ARCADE_LANGCHAIN_TOOLS = [get_arcade_2_x_api_conventions, search_arcade_kb]