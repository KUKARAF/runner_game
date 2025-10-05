# running_game.py
import os
from datetime import datetime, timedelta
from pathlib import Path
from dawarich import Dawarich


class RunningGame:
    def __init__(self, game_name: str,
                 distance_goal_m: float = None,
                 time_goal_min: float = None,
                 base_story_path="stories",
                 progress_path="progress"):
        self.game_name = game_name
        self.distance_goal_m = distance_goal_m
        self.time_goal_min = time_goal_min
        self.story_folder = Path(base_story_path) / game_name
        self.progress_path = Path(progress_path)
        self.dawarich = Dawarich()
        self.start_time = None
        self.start_location = None
        self.session_file = None
        self.total_distance_m = 0.0

    def get_today_folder(self):
        today_folder = self.progress_path / datetime.now().strftime("%Y-%m-%d")
        today_folder.mkdir(parents=True, exist_ok=True)
        return today_folder

    def start(self):
        """Start a new game session."""
        self.start_time = datetime.now()
        self.start_location = self._get_current_location()

        session_filename = f"session_{self.start_time.strftime('%H-%M-%S')}.txt"
        self.session_file = self.get_today_folder() / session_filename

        with open(self.session_file, "w") as f:
            f.write(f"Game: {self.game_name}\n")
            f.write(f"Start time: {self.start_time}\n")
            f.write(f"Start location: {self.start_location}\n")
            if self.distance_goal_m:
                f.write(f"Goal: {self.distance_goal_m/1000:.2f} km\n")
            if self.time_goal_min:
                f.write(f"Time limit: {self.time_goal_min:.0f} min\n")
            f.write("\n=== Progress ===\n")

        print(f"🎮 Game '{self.game_name}' started at {self.start_time}")
        return self.session_file

    def _get_current_location(self):
        """Get current location using Dawarich API."""
        points = self.dawarich.get_points_since(datetime.now().isoformat())
        if points:
            last = points[-1]
            lat, lon = self.dawarich._extract_coords(last)
            return (lat, lon)
        return (0.0, 0.0)

    def update(self):
        """Update current distance and time stats."""
        stats = self.dawarich.since(self.start_time.year,
                                    self.start_time.month,
                                    self.start_time.day)
        if stats and stats["distance_travelled_m"]:
            self.total_distance_m = stats["distance_travelled_m"]
        elapsed = datetime.now() - self.start_time
        elapsed_min = elapsed.total_seconds() / 60

        msg = f"[{datetime.now().strftime('%H:%M:%S')}] " \
              f"Distance: {self.total_distance_m/1000:.2f} km | Time: {elapsed_min:.1f} min"

        with open(self.session_file, "a") as f:
            f.write(msg + "\n")

        print(msg)
        return {"distance_m": self.total_distance_m, "elapsed_min": elapsed_min}

    def _is_success(self, distance_m, elapsed_min):
        """Check if mission succeeded."""
        success = True
        if self.distance_goal_m and distance_m < self.distance_goal_m:
            success = False
        if self.time_goal_min and elapsed_min < self.time_goal_min:
            success = False
        return success

    def end(self):
        """End the session and record result."""
        stats = self.update()
        success = self._is_success(stats["distance_m"], stats["elapsed_min"])
        result = "SUCCESS" if success else "FAILURE"

        with open(self.session_file, "a") as f:
            f.write(f"\n=== Game Ended ===\n")
            f.write(f"End time: {datetime.now()}\n")
            f.write(f"Result: {result}\n")

        print(f"🏁 Game ended with result: {result}")
        return result

