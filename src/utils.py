import os
import re


def clean_code_content(content: str) -> str:
    """
    清洗 LLM 回傳的內容，移除 Markdown 標記與多餘的對話文字。
    """
    # 1. 尋找 Markdown 的程式碼區塊 ```python ... ```
    code_block_match = re.search(r"```python\s+(.*?)\s+```", content, re.DOTALL)
    if code_block_match:
        return code_block_match.group(1).strip()

    # 2. 如果沒找到 python 標籤，找一般的 ``` ... ```
    code_block_match = re.search(r"```\s+(.*?)\s+```", content, re.DOTALL)
    if code_block_match:
        return code_block_match.group(1).strip()

    # 3. 如果連標籤都沒有，檢查是否有解釋性文字
    # 通常程式碼會以 import 或 class 或 def 開頭
    # 這裡我們移除掉所有在第一個 import/class/def 出現之前的文字
    lines = content.split('\n')
    start_index = -1
    for i, line in enumerate(lines):
        if line.strip().startswith(('import ', 'from ', 'class ', 'def ', '"""', "'''")):
            start_index = i
            break

    if start_index != -1:
        return '\n'.join(lines[start_index:]).strip()

    return content.strip()


def save_generated_files(file_dict: dict, base_dir: str):
    """
    儲存檔案前先調用 clean_code_content
    """
    if not os.path.exists(base_dir):
        os.makedirs(base_dir)

    for filename, content in file_dict.items():
        file_path = os.path.join(base_dir, filename)

        # [關鍵] 進行內容清洗
        cleaned_content = clean_code_content(content)

        with open(file_path, "w", encoding="utf-8") as f:
            f.write(cleaned_content)
        print(f"💾 Saved: {file_path}")