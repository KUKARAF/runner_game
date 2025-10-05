from pathlib import Path
from jinja2 import Template
from openai import OpenAI
from datetime import datetime
from settings import OPENROUTER_API_BASE, OPENROUTER_API_KEY, SITE_URL


class VoiceGenerator:
    """
    Voice generator for mission events using OpenRouter and the OpenAI client.
    Generates audio files for mission beginning, interlude, success, and failure.
    """

    def __init__(
        self,
        game_name: str,
        model: str = "openai/gpt-4o",
        site_title: str = "Running Game",
    ):
        self.game_name = game_name
        self.model = model
        self.api_key = OPENROUTER_API_KEY

        if not self.api_key:
            raise ValueError("Missing OPENROUTER_API_KEY in .env")

        # Initialize OpenAI client for OpenRouter
        self.client = OpenAI(
            base_url=OPENROUTER_API_BASE,
            api_key=self.api_key,
        )

        self.extra_headers = {
            "HTTP-Referer": SITE_URL,
            "X-Title": site_title,
        }

        # Template paths for different voice types
        self.template_dir = Path("templates/prompts/voice")
        self.character_path = Path("MAIN_CHARACTER.md")
        self.background_path = Path(f"stories/{game_name}/BACKGROUND.md")

    def _read_file(self, path: Path) -> str:
        """Safely read a file, returning empty string if missing."""
        return path.read_text(encoding="utf-8") if path.exists() else ""

    def _render_prompt(self, voice_type: str, **kwargs) -> str:
        """Render the Jinja2 voice template with context."""
        template_path = self.template_dir / f"{voice_type}.md"
        template_text = self._read_file(template_path)
        template = Template(template_text)

        context = {
            "character": self._read_file(self.character_path),
            "background": self._read_file(self.background_path),
            "game_name": self.game_name,
            **kwargs,
        }

        return template.render(**context)

    def generate_audio(self, voice_type: str, text: str, **kwargs) -> str:
        """Generate audio file from text using OpenRouter's TTS."""
        # For now, we'll use the chat completion API to generate the text to be spoken
        # Then we can use a TTS service to convert it to audio
        # Note: OpenRouter may not support TTS directly, so we might need to adjust this
        # Let's use the same approach as the mission generation for now
        prompt = self._render_prompt(voice_type, **kwargs)

        # Generate the text to be spoken
        completion = self.client.chat.completions.create(
            extra_headers=self.extra_headers,
            model=self.model,
            messages=[
                {"role": "system", "content": "You are a voice actor for an immersive running game."},
                {"role": "user", "content": prompt},
            ],
            temperature=0.9,
        )

        text_to_speak = completion.choices[0].message.content.strip()

        # Save the generated text to a file
        date_str = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
        audio_dir = Path(f"stories/{self.game_name}/audio/{voice_type}")
        audio_dir.mkdir(parents=True, exist_ok=True)

        text_path = audio_dir / f"{date_str}.txt"
        text_path.write_text(text_to_speak, encoding="utf-8")

        # TODO: Add actual TTS generation here when available
        # For now, we'll just return the path to the text file
        return str(text_path)
