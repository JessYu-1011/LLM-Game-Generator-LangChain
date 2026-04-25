import json
from urllib import request
import os
import time
import io

from PIL import Image
from rembg import remove
from src.generation.create_hitbox import generate_hitbox
from src.config import config

BASE_URL = config.COMFYUI_BASE_URL

def picture_generate(name, description, size):
    print("Name : ", name, " | ", "Description : ", description, " | ", "Size : ", size)

    if size[0] < 32 and size[1] < 32: # 圖片極小 (w < 32 AND h < 32)
        print(f"{name} is too small ({size}), using fall back.")
        return 
    
    # ---------- 等比例放大到 >= 512 ----------
    original_size = size.copy() # 記住原尺寸
    w, h = size
    scale = max(512 / w, 512 / h) if (w < 512 or h < 512) else 1
    size = [int(w * scale), int(h * scale)]

    if size[0] > 2048 or size[1] > 2048:  # 圖片特殊 (長寬比超過4倍)
        print(f"{name} is too large ({size}), using fall back.")
        return

    # ---------- 送到 ComfyUI Queue ----------
    with open("./src/generation/comfyUI_prompt.json", "r", encoding="utf-8") as f:
        prompt_json = json.load(f)
    
    prompt_json["7"]["inputs"]["text"] = description  # positive prompt
    prompt_json["8"]["inputs"]["text"] = "blurry, lowres, watermark"  # negative prompt
    prompt_json["9"]["inputs"]["width"] = size[0]  # size
    prompt_json["9"]["inputs"]["height"] = size[1]

    data = json.dumps({"prompt": prompt_json}).encode("utf-8")
    req = request.Request(f"{BASE_URL}/prompt", data=data, headers={"Content-Type": "application/json"})
    response = request.urlopen(req)
    prompt_id = json.loads(response.read())["prompt_id"]

    # ---------- 等待生成完成 ----------
    while True:
        history_url = f"{BASE_URL}/history/{prompt_id}"
        response = request.urlopen(history_url)
        history = json.loads(response.read())
        if prompt_id in history:
            history = history[prompt_id]
            break
        time.sleep(1)

    # ---------- 取得圖片 filename ----------
    outputs = history.get("outputs", {})
    for node_id, node in outputs.items():
        if "images" in node and node["images"]:
            filename = node["images"][0]["filename"]
            break
    else:
        raise ValueError("No image found in history outputs")

    # ---------- 存檔位置 ----------
    project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    pic_dir = os.path.join(project_root, "output_games", "generated_game", "picture")

    os.makedirs(pic_dir, exist_ok=True)
    pic_path = os.path.join(pic_dir, name) + ".png"

    url = f"{BASE_URL}/view?filename={filename}&type=output"
    response = request.urlopen(url)
    raw_data = response.read()

    # ---------- 去白色背景 ----------
    output_no_bg = remove(raw_data)
    
    # ---------- 縮回原尺寸 ----------
    img = Image.open(io.BytesIO(output_no_bg)).convert("RGBA")
    img = img.resize((original_size[0], original_size[1]), Image.Resampling.NEAREST)

    img.save(pic_path, "PNG")
    print("Picture saved to:", pic_path, "Size:", img.size)

    # ---------- 生成 Hitbox ----------
    hitbox_coordinates = generate_hitbox(img, sampling=1)
    
    # ---------- 存檔位置 ----------
    hitbox_dir = os.path.join(project_root, "output_games", "generated_game", "hitbox")
    os.makedirs(hitbox_dir, exist_ok=True)
    hitbox_path = os.path.join(hitbox_dir, name) + ".json"
    with open(hitbox_path, "w") as f:
        json.dump(hitbox_coordinates, f)

    print("Hitbox saved to:", hitbox_path)