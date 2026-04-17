import sys
import os
from flask import Flask, render_template, request, jsonify
from flask_socketio import SocketIO

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))

from src.config import config
from src.generation.core.core import run_full_generator_pipeline
from src.utils import save_generated_files

app = Flask(__name__, template_folder="templates", static_folder="static")
app.config['SECRET_KEY'] = config.SECRET_KEY

# Use 'threading' async_mode to ensure compatibility with standard Flask execution
socketio = SocketIO(app, cors_allowed_origins="*", async_mode='threading')
providers = ["mistral", "openai", "groq", "google", "deepseek", "inception"]

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


@app.route('/generate', methods=['POST'])
def generate_game():
    """
    Handle the game generation request.
    This triggers the full pipeline: Design -> Asset -> Code -> Test.
    """
    data = request.json
    user_idea = data.get('idea', 'A simple pong game')
    selected_provider = data.get('provider', 'mistral')

    stream_log(f"Starting Game Generation using [{selected_provider.upper()}] for: {user_idea}")

    try:
        # Execute the full generation pipeline.
        # This encapsulates Design, Asset Generation, Coding, and Testing phases.
        project_files = run_full_generator_pipeline(
            user_idea,
            log_callback=stream_log,
            provider=selected_provider
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
    # Use allow_unsafe_werkzeug=True to run with the Flask development server
    socketio.run(app, debug=False, port=5000, allow_unsafe_werkzeug=True)