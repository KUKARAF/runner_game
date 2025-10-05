from flask import Flask, jsonify, send_from_directory
import time
import threading
from pathlib import Path
from llm import Mission
from voices import VoiceGenerator
from settings import MONITOR_INTERVAL

app = Flask(__name__)

# Create a mission instance
mission = Mission(
    game_name="zombies",
    mode="distance",
    target_value=5,
    site_title="Zombie Runner",
)

# Start the mission
mission.start()

# Global variables to track mission status
mission_status = {
    "distance_m": 0.0,
    "elapsed_min": 0.0,
    "is_success": False,
    "is_failure": False,
    "is_active": True
}

# Track audio files
audio_files = []

def monitor_mission():
    """Monitor mission progress and update status"""
    global mission_status
    while mission_status["is_active"]:
        # Update the mission to get current distance and time
        stats = mission.update()
        
        # Get current distance and elapsed time from the returned dictionary
        distance_m = stats["distance_m"]
        elapsed_min = stats["elapsed_min"]
        
        # Update status
        mission_status["distance_m"] = distance_m
        mission_status["elapsed_min"] = elapsed_min
        
        # Check if target is reached
        if mission._is_success(distance_m, elapsed_min):
            mission_status["is_success"] = True
            mission_status["is_active"] = False
            # Generate success audio
            voice_gen = VoiceGenerator(game_name="zombies")
            voice_gen.generate_audio("success", "")
        
        # Sleep for configured interval
        time.sleep(MONITOR_INTERVAL)

# Start monitoring in a separate thread
monitor_thread = threading.Thread(target=monitor_mission)
monitor_thread.daemon = True
monitor_thread.start()

@app.route('/mission/<mission_name>/status')
def get_mission_status(mission_name):
    """Return current mission status as JSON"""
    return jsonify(mission_status)

@app.route('/mission/<mission_name>/audio')
def get_mission_audio(mission_name):
    """Return list of audio files with their status"""
    # Scan the audio directory
    audio_dir = Path(f"stories/{mission_name}/audio")
    if not audio_dir.exists():
        return jsonify([])
    
    # This is a simplified implementation
    # You'd want to track which files have been played
    audio_files = []
    for voice_type in ["beginning", "interlude", "success", "failure"]:
        type_dir = audio_dir / voice_type
        if type_dir.exists():
            files = list(type_dir.glob("*.txt"))
            if files:
                # Get the latest file
                latest_file = max(files, key=lambda x: x.stat().st_mtime)
                audio_files.append({
                    "url": f"/audio/{mission_name}/{voice_type}/{latest_file.name}",
                    "status": "new",  # This needs to be tracked per user
                    "type": voice_type
                })
    return jsonify(audio_files)

@app.route('/audio/<mission_name>/<voice_type>/<filename>')
def serve_audio(mission_name, voice_type, filename):
    """Serve audio files"""
    return send_from_directory(f"stories/{mission_name}/audio/{voice_type}", filename)

if __name__ == '__main__':
    app.run(debug=True)
