import sys
import os
from flask import Flask, render_template, request, jsonify
from flask_socketio import SocketIO

# 確保可以找到 src 模組
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))

from src.config import config
from src.generation.core import run_design_phase, run_production_pipeline, run_test_and_fix_phase
from src.generation.asset_gen import generate_assets
from src.utils import save_generated_files

app = Flask(__name__, template_folder="templates", static_folder="static")
app.config['SECRET_KEY'] = config.SECRET_KEY

# 使用 threading 模式確保兼容性
socketio = SocketIO(app, cors_allowed_origins="*", async_mode='threading')


def stream_log(message):
    """將 Log 推送到前端"""
    print(message)
    socketio.emit('agent_log', {'data': message})


@app.route('/')
def index():
    return render_template('index.html')


@app.route('/generate', methods=['POST'])
def generate_game():
    data = request.json
    user_idea = data.get('idea', 'A simple pong game')

    # [NEW] 獲取前端傳來的 provider，預設為 openai
    selected_provider = data.get('provider', 'openai')

    stream_log(f"🚀 Starting Game Generation using [{selected_provider.upper()}] for: {user_idea}")

    # 1. Design Phase (傳入 provider)
    # 這裡 model 設為 None，讓 model_factory 自動去 config 抓該 provider 的預設模型
    gdd = run_design_phase(user_idea, log_callback=stream_log, provider=selected_provider, model=None)

    # 2. Asset Phase (傳入 provider)
    stream_log("🎨 Generating Assets...")
    # 注意：asset_gen 如果有 provider 參數也要傳，目前簡單處理
    assets = generate_assets(gdd, provider=selected_provider)

    # 3. Production Phase (傳入 provider)
    stream_log("⚙️ Starting Production Pipeline...")
    files = run_production_pipeline(gdd, assets, log_callback=stream_log, provider=selected_provider, model=None)

    # 4. Test & Fix Phase (傳入 provider)
    stream_log("🧪 Running Fuzzer & Auto-Fixer...")
    output_path = os.path.join(config.OUTPUT_DIR, "generated_game")

    if not os.path.exists(output_path):
        os.makedirs(output_path)

    # 測試階段也使用選定的 Provider 進行修復
    files = run_test_and_fix_phase(files, output_path, log_callback=stream_log, provider=selected_provider, model=None)

    # 5. Final Save
    stream_log("💾 Saving final files...")
    path = save_generated_files(files, output_path)

    stream_log(f"✅ Done! Game saved at: {path}")
    return jsonify({"status": "success", "path": path})


if __name__ == '__main__':
    socketio.run(app, debug=True, port=5000, allow_unsafe_werkzeug=True)