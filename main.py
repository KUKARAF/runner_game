from llm import Mission

mission = Mission(
    game_name="zombies",
    mode="distance",
    target_value=5,
    site_title="Zombie Runner",
)

mission_text = mission.generate_mission()
# amazint! that worked! now we need to: 1. expose a endpoint that shows our mission status (we need a urls.py file for that) /mission/mission_name/status (just reply with json) 2. expose a endpoint that shows all audio tracks per mission (json with url.mp3, status (new: latest not played, played: latest played, stale: old completed mission) we then need to add a for loop that check every x minutes (configured in settings) how much distance and how much time passed and if we reached our target (if yes start success condition) AI!
#print(mission_text)

