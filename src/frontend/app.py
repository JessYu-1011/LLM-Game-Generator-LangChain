import sys
import os
import time
import json

from flask import Flask, render_template, request, jsonify
from flask_socketio import SocketIO

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))

from src.config import config
from src.generation.core.core import run_full_generator_pipeline
from src.utils import save_generated_files, api_status

app = Flask(__name__, template_folder="templates", static_folder="static")
app.config['SECRET_KEY'] = config.SECRET_KEY

# Use 'threading' async_mode to ensure compatibility with standard Flask execution
socketio = SocketIO(app, cors_allowed_origins="*", async_mode='threading')
providers = ["mistral", "openai", "groq", "google", "deepseek", "inception", "claude", "ollama"]


def stream_log(message):
    """
    Push logs to the frontend via SocketIO.
    This provides real-time feedback to the user interface.
    """
    print(message)
    socketio.emit('agent_log', {'data': message})


@app.route('/')
def index():
    """Render the main page."""
    return render_template('index.html', providers=providers)


@app.route('/save_settings', methods=['POST'])
def save_settings():
    """將網頁上的設定儲存到 cache 資料夾中"""
    try:
        config_data = request.json
        cache_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "../../cache"))

        # 確保 cache 資料夾存在
        if not os.path.exists(cache_dir):
            os.makedirs(cache_dir)

        file_path = os.path.join(cache_dir, "llm_config.json")

        with open(file_path, "w", encoding="utf-8") as f:
            json.dump(config_data, f, indent=4)

        return jsonify({"status": "success", "message": "Settings saved to cache folder"})
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500


@app.route('/load_settings', methods=['GET'])
def load_settings():
    """從 cache 資料夾中讀取設定檔並回傳給網頁"""
    try:
        cache_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "../../cache"))
        file_path = os.path.join(cache_dir, "llm_config.json")

        if os.path.exists(file_path):
            with open(file_path, "r", encoding="utf-8") as f:
                config_data = json.load(f)
            return jsonify({"status": "success", "config": config_data})
        else:
            return jsonify({"status": "error", "message": "No cache file found"})
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500


@app.route('/generate', methods=['POST'])
def generate_game():
    """
    Handle the game generation request.
    This triggers the full pipeline: Design -> Asset -> Code -> Test.
    """
    data = request.json
    user_idea = data.get('idea', 'A simple pong game')

    # Retrieve default and chain-specific configs with fallback defaults
    default_config: dict = data.get('default_config', {
        'provider': 'mistral',
        'model': 'codestral-latest',
        'temperature': 0.2,
        'using_picture_generate': False
    })
    chain_configs = data.get('chain_configs', {})

    # [NEW] 動態覆蓋 config 裡的設定，以網頁傳來的設定為準
    if 'using_picture_generate' in default_config:
        config.USING_PICTURE_GENERATE = default_config['using_picture_generate']
        stream_log(f"Overriding config.USING_PICTURE_GENERATE -> {config.USING_PICTURE_GENERATE}")

    default_config.pop('using_picture_generate')

    stream_log(f"Starting Generation for: {user_idea}")
    stream_log(f"Default LLM Config: {default_config}")

    if chain_configs:
        stream_log(f"Overridden Chain Configs: {len(chain_configs)} chains specified.")

    try:
        # Execute the full generation pipeline.
        # Ensure run_full_generator_pipeline is updated to receive these config dicts.
        project_files = run_full_generator_pipeline(
            user_idea,
            log_callback=stream_log,
            default_config=default_config,
            chain_configs=chain_configs
        )

        # Save the finalized files to the output directory
        stream_log("Saving final files...")
        output_path = os.path.join(config.OUTPUT_DIR, "generated_game")

        if not os.path.exists(output_path):
            os.makedirs(output_path)

        saved_path = save_generated_files(project_files, output_path)

        stream_log(f"Done! Game saved at: {saved_path}")
        return jsonify({"status": "success", "path": saved_path})

    except Exception as e:
        error_msg = f"Error during generation: {str(e)}"
        stream_log(error_msg)
        return jsonify({"status": "error", "message": error_msg}), 500


if __name__ == '__main__':
    # Send request to ComfyUI, if it's not started, telling the user to start.
    # comfyui_is_online = False
    # while not comfyui_is_online:
    #     comfyui_is_online = api_status("ComfyUI", config.COMFYUI_BASE_URL, stream_log)
    #     time.sleep(3)

    # Use allow_unsafe_werkzeug=True to run with the Flask development server
    socketio.run(app, debug=False, port=5000, allow_unsafe_werkzeug=True)