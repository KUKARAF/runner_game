from pathlib import Path
from datetime import datetime
from typing import Optional, Dict
import mimetypes
import os
import struct

from jinja2 import Template
from google import genai
from google.genai import types


class VoiceGenerator:
    """
    Voice generator for mission events using Google Gemini TTS.
    Generates audio files for mission beginning, interlude, success, and failure.

    Workflow:
      1. Render narration text from Jinja templates (or consume provided text).
      2. Use Gemini TTS to synthesize speech.
      3. Store both audio and transcript on disk.
    """

    def __init__(
        self,
        game_name: str,
        model: str = "gemini-2.5-pro-preview-tts",
        site_title: str = "Running Game",  # retained for backwards compatibility
        language: str = "en",  # preserved but not currently used directly by Gemini TTS
        default_voice: str = "Leda",
        temperature: float = 1.0,
    ):
        self.game_name = game_name
        self.model = model
        self.language = language
        self.default_voice = default_voice
        self.temperature = temperature

        api_key = os.environ.get("GEMINI_API_KEY")
        if not api_key:
            raise ValueError("Missing GEMINI_API_KEY in environment variables")

        self.client = genai.Client(api_key=api_key)

        # Template paths for different voice types
        self.template_dir = Path("templates/prompts/voice")
        self.character_path = Path("MAIN_CHARACTER.md")
        self.background_path = Path(f"stories/{game_name}/BACKGROUND.md")

    def _read_file(self, path: Path) -> str:
        """Safely read a file, returning empty string if missing."""
        return path.read_text(encoding="utf-8") if path.exists() else ""

    def _render_script(self, voice_type: str, **kwargs) -> str:
        """Render the Jinja2 voice template with context."""
        template_path = self.template_dir / f"{voice_type}.md"
        if not template_path.exists():
            return ""

        template_text = self._read_file(template_path)
        template = Template(template_text)

        context = {
            "character": self._read_file(self.character_path),
            "background": self._read_file(self.background_path),
            "game_name": self.game_name,
            **kwargs,
        }

        return template.render(**context).strip()

    def generate_audio(
        self,
        voice_type: str,
        text: Optional[str] = None,
        *,
        voice_name: Optional[str] = None,
        temperature: Optional[float] = None,
        **kwargs,
    ) -> str:
        """
        Generate audio for the supplied or template-rendered narration text.

        Args:
            voice_type: Template name used to guide the narration style.
            text: Optional narration text. When omitted, a template is rendered.
            voice_name: Optional override for the Gemini voice name.
            temperature: Optional override for sampling temperature.
            **kwargs: Extra template variables.

        Returns:
            str: Path to the generated audio file on disk.
        """
        narration = (text or "").strip()
        if not narration:
            narration = self._render_script(voice_type, **kwargs)

        if not narration:
            raise ValueError(
                "No narration text provided and no template content available for "
                f"voice type '{voice_type}'."
            )

        resolved_voice_name = voice_name or self.default_voice
        resolved_temperature = (
            self.temperature if temperature is None else max(0.0, min(2.0, temperature))
        )

        contents = [
            types.Content(
                role="user",
                parts=[
                    types.Part.from_text(text=narration),
                ],
            ),
        ]

        config = types.GenerateContentConfig(
            temperature=resolved_temperature,
            response_modalities=["audio"],
            speech_config=types.SpeechConfig(
                voice_config=types.VoiceConfig(
                    prebuilt_voice_config=types.PrebuiltVoiceConfig(
                        voice_name=resolved_voice_name
                    )
                )
            ),
        )

        audio_bytes = bytearray()
        audio_mime_type: Optional[str] = None
        supplemental_text: list[str] = []

        stream = self.client.models.generate_content_stream(
            model=self.model,
            contents=contents,
            config=config,
        )

        for chunk in stream:
            if (
                not chunk.candidates
                or not chunk.candidates[0].content
                or not chunk.candidates[0].content.parts
            ):
                continue

            for part in chunk.candidates[0].content.parts:
                inline_data = getattr(part, "inline_data", None)
                if inline_data and inline_data.data:
                    if audio_mime_type is None:
                        audio_mime_type = inline_data.mime_type
                    audio_bytes.extend(inline_data.data)
                else:
                    text_part = getattr(part, "text", None)
                    if text_part:
                        supplemental_text.append(text_part)

        if not audio_bytes:
            raise RuntimeError("No audio data returned from Google Gemini TTS.")

        audio_data = bytes(audio_bytes)
        extension = None

        if audio_mime_type:
            extension = mimetypes.guess_extension(audio_mime_type)

        if extension is None:
            audio_data = convert_to_wav(
                audio_data, audio_mime_type or "audio/L16;rate=24000"
            )
            extension = ".wav"

        timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
        audio_dir = Path(f"stories/{self.game_name}/audio/{voice_type}")
        audio_dir.mkdir(parents=True, exist_ok=True)

        audio_path = audio_dir / f"{timestamp}{extension}"
        audio_path.write_bytes(audio_data)

        transcript_path = audio_dir / f"{timestamp}.txt"
        transcript_parts = [narration]
        if supplemental_text:
            transcript_parts.append("\n".join(supplemental_text))
        transcript_path.write_text("\n\n".join(transcript_parts), encoding="utf-8")

        return str(audio_path)


def convert_to_wav(audio_data: bytes, mime_type: str) -> bytes:
    """Wrap raw PCM audio data with a WAV header."""
    parameters = parse_audio_mime_type(mime_type)
    bits_per_sample = parameters["bits_per_sample"] or 16
    sample_rate = parameters["rate"] or 24000
    num_channels = 1

    data_size = len(audio_data)
    bytes_per_sample = bits_per_sample // 8
    block_align = num_channels * bytes_per_sample
    byte_rate = sample_rate * block_align
    chunk_size = 36 + data_size

    header = struct.pack(
        "<4sI4s4sIHHIIHH4sI",
        b"RIFF",
        chunk_size,
        b"WAVE",
        b"fmt ",
        16,
        1,
        num_channels,
        sample_rate,
        byte_rate,
        block_align,
        bits_per_sample,
        b"data",
        data_size,
    )
    return header + audio_data


def parse_audio_mime_type(mime_type: str) -> Dict[str, Optional[int]]:
    """Extract bits per sample and sample rate from an audio MIME type string."""
    bits_per_sample: Optional[int] = None
    rate: Optional[int] = None

    if not mime_type:
        return {"bits_per_sample": bits_per_sample, "rate": rate}

    parts = [segment.strip() for segment in mime_type.split(";") if segment.strip()]
    for segment in parts:
        lower = segment.lower()
        if lower.startswith("rate="):
            try:
                rate = int(segment.split("=", 1)[1])
            except (ValueError, IndexError):
                continue
        elif lower.startswith("audio/l"):
            try:
                bits_per_sample = int(segment.split("l", 1)[1])
            except (ValueError, IndexError):
                continue

    return {"bits_per_sample": bits_per_sample, "rate": rate}
