import sys
import os
from flask import Flask, render_template, request, jsonify
from flask_socketio import SocketIO
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))

from src.config import config
from src.generation.core import run_design_phase, run_production_pipeline, run_test_and_fix_phase
from src.generation.asset_gen import generate_assets
from src.utils import save_generated_files

app = Flask(__name__, template_folder="templates", static_folder="static")
app.config['SECRET_KEY'] = config.SECRET_KEY

socketio = SocketIO(app, cors_allowed_origins="*", async_mode='threading')


def stream_log(message):
    """Push logs to the frontend via SocketIO"""
    print(message)
    socketio.emit('agent_log', {'data': message})


@app.route('/')
def index():
    return render_template('index.html')


@app.route('/generate', methods=['POST'])
def generate_game():
    data = request.json
    user_idea = data.get('idea', 'A simple pong game')

    selected_provider = data.get('provider', 'openai')

    stream_log(f"Starting Game Generation using [{selected_provider.upper()}] for: {user_idea}")

    # 1. Design Phase
    gdd = run_design_phase(user_idea, log_callback=stream_log, provider=selected_provider, model=None)

    # 2. Asset Phas
    stream_log("Generating Assets...")
    assets = generate_assets(gdd, provider=selected_provider)

    # 3. Production Phase
    stream_log("Starting Production Pipeline...")
    files = run_production_pipeline(gdd, assets, log_callback=stream_log, provider=selected_provider, model=None)

    # 4. Test & Fix Phase
    stream_log("Running Fuzzer & Auto-Fixer...")
    output_path = os.path.join(config.OUTPUT_DIR, "generated_game")

    if not os.path.exists(output_path):
        os.makedirs(output_path)

    files = run_test_and_fix_phase(files, output_path, log_callback=stream_log, provider=selected_provider, model=None)

    # 5. Final Save
    stream_log("Saving final files...")
    path = save_generated_files(files, output_path)

    stream_log(f"Done! Game saved at: {path}")
    return jsonify({"status": "success", "path": path})


if __name__ == '__main__':
    socketio.run(app, debug=False, port=5000, allow_unsafe_werkzeug=True)