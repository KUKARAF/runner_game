from llm import Mission

mission = Mission(
    game_name="zombies",
    mode="distance",
    target_value=5,
    site_title="Zombie Runner",
)

mission_text = mission.generate_mission()
print(mission_text)

