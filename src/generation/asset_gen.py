import json
import re
from src.generation.picture_generate import picture_generate


def generate_assets(
        response: str,
        log_callback = print,
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


    try:
        log_callback("[AssetGen]")
        log_callback("=== RAW OUTPUT ===")
        # print(response)

        json_match = re.search(r"\{.*\}", response, re.DOTALL)
        if not json_match:
            return "{}"

        assets_json_str = json_match.group(0)
        assets = json.loads(assets_json_str)

        # === 檢查每個 asset ===
        for name, asset in assets.items():

            if "describe" in asset:
                log_callback(f"[AssetGen] Generating image for: {name}")

                description = asset["describe"]
                size = asset.get("size", [64, 64])

                filename = picture_generate(name, description, size, log_callback=log_callback)
                # 可選：把 filename 記錄回 JSON
                asset["filename"] = filename

        return json.dumps(assets, indent=2)

    except Exception as e:
        log_callback(f"[AssetGen Error] {e}")
        return "{}"