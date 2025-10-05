from pathlib import Path
from jinja2 import Template
from openai import OpenAI
from datetime import datetime

from game import RunningGame  # your base class
from settings import OPENROUTER_API_BASE, OPENROUTER_API_KEY, SITE_URL

class Mission(RunningGame):
    """
    Mission generator using OpenRouter and the OpenAI client.
    Inherits from RunningGame and uses Jinja templates for story generation.
    """

    def __init__(
        self,
        game_name: str,
        mode: str = "distance",
        target_value: float = 0.0,
        model: str = "openai/gpt-4o",
        site_title: str = "Running Game",
    ):
        super().__init__(game_name, mode, target_value)

        self.model = model
        self.api_key = OPENROUTER_API_KEY

        if not self.api_key:
            raise ValueError("Missing OPENROUTER_API_KEY in .env")

        # Initialize OpenAI client for OpenRouter
        self.client = OpenAI(
            base_url=OPENROUTER_API_BASE,
            api_key=self.api_key,
        )

        # For rankings & attribution on openrouter.ai
        self.extra_headers = {
            "HTTP-Referer": SITE_URL,
            "X-Title": site_title,
        }

        # File paths
        self.template_path = Path("templates/prompts/story_generator.md")
        self.character_path = Path("MAIN_CHARACTER.md")
        self.background_path = Path(f"stories/{game_name}/BACKGROUND.md")

    def _read_file(self, path: Path) -> str:
        """Safely read a file, returning empty string if missing."""
        return path.read_text(encoding="utf-8") if path.exists() else ""

    def _render_prompt(self, **kwargs) -> str:
        """Render the Jinja2 story template with context."""
        template_text = self._read_file(self.template_path)
        template = Template(template_text)

        context = {
            "character": self._read_file(self.character_path),
            "background": self._read_file(self.background_path),
            "mode": self.mode,
            "target_value": self.target_value,
            "game_name": self.game_name,
            **kwargs,
        }

        return template.render(**context)

    def generate_mission(self, **kwargs) -> str:
        """Generate a mission story using OpenRouter and save it."""
        prompt = self._render_prompt(**kwargs)

        completion = self.client.chat.completions.create(
            extra_headers=self.extra_headers,
            model=self.model,
            messages=[
                {"role": "system", "content": "You are a creative AI that generates immersive running missions."},
                {"role": "user", "content": prompt},
            ],
            temperature=0.9,
        )

        story = completion.choices[0].message.content.strip()

        # Save the story to file
        date_str = datetime.now().strftime("%Y-%m-%d")
        story_dir = Path(f"stories/{self.game_name}/missions")
        story_dir.mkdir(parents=True, exist_ok=True)

        story_path = story_dir / f"{date_str}.txt"
        story_path.write_text(story, encoding="utf-8")

        return story

