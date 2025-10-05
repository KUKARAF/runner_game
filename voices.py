from pathlib import Path
from typing import Optional

from datetime import datetime
from gtts import gTTS
from jinja2 import Template
from openai import OpenAI
from settings import OPENROUTER_API_BASE, OPENROUTER_API_KEY, SITE_URL


class VoiceGenerator:
    """
    Voice generator for mission events using OpenRouter and the OpenAI client.
    Generates audio files for mission beginning, interlude, success, and failure.

    Workflow:
      1. Render a voice prompt from Jinja templates.
      2. Ask the LLM to produce narration text (unless text is supplied directly).
      3. Synthesize speech using gTTS and store both audio (.mp3) and transcript (.txt).
    """

    def __init__(
        self,
        game_name: str,
        model: str = "openai/gpt-4o",
        site_title: str = "Running Game",
        language: str = "en",
    ):
        self.game_name = game_name
        self.model = model
        self.api_key = OPENROUTER_API_KEY
        self.language = language

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

    def _generate_voice_script(self, voice_type: str, **kwargs) -> str:
        """Use the LLM to generate narration text for the given voice type."""
        prompt = self._render_prompt(voice_type, **kwargs)

        completion = self.client.chat.completions.create(
            extra_headers=self.extra_headers,
            model=self.model,
            messages=[
                {
                    "role": "system",
                    "content": "You are a voice actor for an immersive running game.",
                },
                {"role": "user", "content": prompt},
            ],
            temperature=0.9,
        )

        return completion.choices[0].message.content.strip()

    def generate_audio(
        self, voice_type: str, text: Optional[str] = None, **kwargs
    ) -> str:
        """
        Generate audio for the supplied or LLM-generated narration text.

        Args:
            voice_type: Template name used to guide the narration style.
            text: Optional narration text. When omitted, the LLM is queried.
            **kwargs: Extra template variables.

        Returns:
            str: Path to the generated audio file on disk.
        """
        text_to_speak = text.strip() if text and text.strip() else self._generate_voice_script(voice_type, **kwargs)

        # Save transcript and audio assets
        date_str = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
        audio_dir = Path(f"stories/{self.game_name}/audio/{voice_type}")
        audio_dir.mkdir(parents=True, exist_ok=True)

        transcript_path = audio_dir / f"{date_str}.txt"
        transcript_path.write_text(text_to_speak, encoding="utf-8")

        audio_path = audio_dir / f"{date_str}.mp3"
        tts = gTTS(text=text_to_speak, lang=self.language)
        tts.save(str(audio_path))

        return str(audio_path)
