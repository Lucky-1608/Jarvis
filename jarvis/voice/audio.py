"""
Jarvis OS — Audio I/O Utilities.

Low-level audio capture (microphone) and playback helpers.
Used by the STT, TTS, and wake word modules.
"""

from __future__ import annotations

import asyncio
import io
import tempfile
import wave
from pathlib import Path

import structlog

logger = structlog.get_logger(__name__)

# Audio constants
SAMPLE_RATE = 16000
CHANNELS = 1
SAMPLE_WIDTH = 2  # 16-bit
CHUNK_SIZE = 1024  # frames per buffer


class AudioRecorder:
    """
    Capture audio from the microphone.

    Uses ``sounddevice`` for cross-platform audio input.
    Records in 16kHz mono PCM — the format faster-whisper expects.
    """

    def __init__(self, sample_rate: int = SAMPLE_RATE, channels: int = CHANNELS) -> None:
        self._sample_rate = sample_rate
        self._channels = channels
        self._recording = False
        self._frames: list[bytes] = []

    async def record_until_silence(
        self,
        silence_threshold: float = 0.01,
        silence_duration: float = 1.5,
        max_duration: float = 30.0,
    ) -> bytes:
        """
        Record audio until silence is detected or max duration is hit.

        Returns raw PCM audio bytes (16kHz, mono, 16-bit).
        """
        try:
            import numpy as np
            import sounddevice as sd
        except ImportError:
            raise RuntimeError(
                "sounddevice is required for audio recording. "
                "Install with: pip install 'jarvis-os[voice]'"
            )

        self._frames = []
        self._recording = True
        silent_chunks = 0
        chunks_per_second = self._sample_rate // CHUNK_SIZE
        max_silent_chunks = int(silence_duration * chunks_per_second)
        max_initial_silent_chunks = int(10.0 * chunks_per_second) # 10s wait for speech to start
        max_chunks = int(max_duration * chunks_per_second)
        total_chunks = 0
        has_spoken = False

        logger.debug("audio.recording_started")

        def callback(indata, frames, time_info, status):
            nonlocal silent_chunks, total_chunks, has_spoken
            if status:
                logger.warning("audio.status", status=str(status))

            audio_data = indata.copy()
            self._frames.append(audio_data.tobytes())
            total_chunks += 1

            # Check for silence (normalize int16 to float32 [-1.0, 1.0])
            audio_float = audio_data.astype(np.float32) / 32768.0
            volume = np.sqrt(np.mean(audio_float**2))

            if volume < silence_threshold:
                silent_chunks += 1
            else:
                silent_chunks = 0
                has_spoken = True # User started speaking

        stream = sd.InputStream(
            samplerate=self._sample_rate,
            channels=self._channels,
            dtype="int16",
            blocksize=CHUNK_SIZE,
            callback=callback,
        )

        with stream:
            while self._recording:
                await asyncio.sleep(0.05)
                # If they have spoken, wait for normal silence duration (1.5s) to stop.
                # If they haven't spoken, wait up to 10s before timing out.
                if has_spoken and silent_chunks >= max_silent_chunks:
                    break
                elif not has_spoken and silent_chunks >= max_initial_silent_chunks:
                    break
                if total_chunks >= max_chunks:
                    break

        self._recording = False
        audio_bytes = b"".join(self._frames)
        duration = len(audio_bytes) / (self._sample_rate * self._channels * SAMPLE_WIDTH)
        logger.info("audio.recording_stopped", duration_s=round(duration, 2))
        return audio_bytes

    def stop(self) -> None:
        """Stop any ongoing recording."""
        self._recording = False


class AudioPlayer:
    """
    Play audio through the system speakers.

    Supports playing from file paths or raw bytes.
    """

    @staticmethod
    async def play_file(filepath: str | Path) -> None:
        """Play an audio file (WAV/MP3)."""
        filepath = Path(filepath)
        if not filepath.exists():
            raise FileNotFoundError(f"Audio file not found: {filepath}")

        try:
            import numpy as np
            import sounddevice as sd

            # Read WAV file
            with wave.open(str(filepath), "rb") as wf:
                frames = wf.readframes(wf.getnframes())
                sample_rate = wf.getframerate()
                channels = wf.getnchannels()
                sample_width = wf.getsampwidth()

            dtype = {1: "int8", 2: "int16", 4: "int32"}.get(sample_width, "int16")
            audio = np.frombuffer(frames, dtype=dtype)
            if channels > 1:
                audio = audio.reshape(-1, channels)

            # Play asynchronously
            event = asyncio.Event()

            def finished_callback(*args):
                event.set()

            sd.play(audio, samplerate=sample_rate, blocking=False)
            sd.wait()

        except ImportError:
            # Fallback: use system command
            import platform
            import subprocess

            system = platform.system()
            if system == "Windows":
                # Use PowerShell to play audio
                subprocess.Popen(
                    ["powershell", "-c", f"(New-Object Media.SoundPlayer '{filepath}').PlaySync()"],
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL,
                )
            elif system == "Darwin":
                subprocess.Popen(["afplay", str(filepath)])
            else:
                subprocess.Popen(["aplay", str(filepath)])

    @staticmethod
    async def play_bytes(audio_bytes: bytes, sample_rate: int = 24000) -> None:
        """Play raw PCM audio bytes."""
        # Write to temp WAV file and play
        with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as tmp:
            tmp_path = tmp.name
            with wave.open(tmp_path, "wb") as wf:
                wf.setnchannels(1)
                wf.setsampwidth(2)
                wf.setframerate(sample_rate)
                wf.writeframes(audio_bytes)

        try:
            await AudioPlayer.play_file(tmp_path)
        finally:
            Path(tmp_path).unlink(missing_ok=True)


def pcm_to_wav(pcm_bytes: bytes, sample_rate: int = SAMPLE_RATE, channels: int = 1) -> bytes:
    """Convert raw PCM bytes to WAV format (in memory)."""
    buffer = io.BytesIO()
    with wave.open(buffer, "wb") as wf:
        wf.setnchannels(channels)
        wf.setsampwidth(SAMPLE_WIDTH)
        wf.setframerate(sample_rate)
        wf.writeframes(pcm_bytes)
    return buffer.getvalue()
