import json
import re

from langchain_core.messages import SystemMessage
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser
from src.generation.model_factory import get_langchain_model
from src.generation.picture_generate import picture_generate
from src.prompts.code_generation_prompts import ART_PROMPT


def generate_assets(
        gdd_context: str,
        provider: str = "openai",
) -> str:
    """
    Generate the art assets for this specific game using the LangChain factory.
    A diffusion model will generate images based on the descriptions.
    Return valid JSON object.

    Each asset MUST contain ONLY TWO keys:
    - "describe": a single short sentence describing the image
    - "size": [width, height] in pixels

    Do NOT include "shape".
    Do NOT include "color".
    Return pure JSON only.
    Example format:
    {
        "background_picture": {
            "describe": "a wooden house in a forest",
            "size": [800, 600]
        },
        "player": {
            "describe": "a knight with silver armor",
            "size": [200, 200]
        },
        "enemy": {
            "describe": "a blue cube",
            "size": [50, 50]
        }
    }
    """
    # Use the unified factory to get the correct model for the provider
    llm = get_langchain_model(provider=provider, temperature=0.5)

    prompt = ChatPromptTemplate.from_messages([
        SystemMessage(content=ART_PROMPT),
        ("user", "GDD Content:\n{gdd}")
    ])

    chain = prompt | llm | StrOutputParser()

    try:
        response = chain.invoke({"gdd": gdd_context})
        
        print("=== RAW OUTPUT ===")
        # print(response)

        json_match = re.search(r"\{.*\}", response, re.DOTALL)
        if not json_match:
            return "{}"

        assets_json_str = json_match.group(0)
        assets = json.loads(assets_json_str)

        # === 檢查每個 asset ===
        for name, asset in assets.items():

            if "describe" in asset:
                print(f"[AssetGen] Generating image for: {name}")

                description = asset["describe"]
                size = asset.get("size", [64, 64])

                filename = picture_generate(name, description, size)
                # 可選：把 filename 記錄回 JSON
                asset["filename"] = filename

        return json.dumps(assets, indent=2)

    except Exception as e:
        print(f"[AssetGen Error] {e}")
        return "{}"