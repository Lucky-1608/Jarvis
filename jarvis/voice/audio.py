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
    Records in 16kHz mono PCM format.
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
        speech_chunks = 0
        has_spoken = False

        logger.debug("audio.recording_started")

        def callback(indata, frames, time_info, status):
            nonlocal silent_chunks, total_chunks, has_spoken, speech_chunks
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
                speech_chunks = 0
            else:
                silent_chunks = 0
                speech_chunks += 1
                if speech_chunks >= 2 or volume > (silence_threshold * 2):
                    has_spoken = True  # User started speaking

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

    async def record_speech_segment(
        self,
        energy_threshold: float = 0.015,
        silence_duration: float = 0.6,
        max_duration: float = 3.2,
        listen_timeout: float = 1.8,
    ) -> bytes | None:
        """
        Record a speech segment if detected within listen_timeout.
        If no speech is detected (ambient noise or silence), returns None
        without wasting STT API calls.
        """
        try:
            import numpy as np
            import sounddevice as sd
        except ImportError:
            raise RuntimeError("sounddevice is required for audio recording.")

        self._frames = []
        pre_buffer: list[bytes] = []
        max_pre_chunks = 6  # ~0.4s pre-speech buffer to retain the beginning of words
        self._recording = True
        silent_chunks = 0
        chunks_per_second = self._sample_rate // CHUNK_SIZE
        max_silent_chunks = int(silence_duration * chunks_per_second)
        max_listen_chunks = int(listen_timeout * chunks_per_second)
        max_chunks = int(max_duration * chunks_per_second)
        total_chunks = 0
        speech_chunks = 0
        has_spoken = False

        def callback(indata, frames, time_info, status):
            nonlocal silent_chunks, total_chunks, has_spoken, speech_chunks
            audio_data = indata.copy()
            total_chunks += 1

            audio_float = audio_data.astype(np.float32) / 32768.0
            volume = np.sqrt(np.mean(audio_float**2))

            if volume > energy_threshold:
                silent_chunks = 0
                speech_chunks += 1
                if speech_chunks >= 2:
                    has_spoken = True
            else:
                silent_chunks += 1
                speech_chunks = 0

            if has_spoken:
                if pre_buffer:
                    self._frames.extend(pre_buffer)
                    pre_buffer.clear()
                self._frames.append(audio_data.tobytes())
            else:
                pre_buffer.append(audio_data.tobytes())
                if len(pre_buffer) > max_pre_chunks:
                    pre_buffer.pop(0)

        stream = sd.InputStream(
            samplerate=self._sample_rate,
            channels=self._channels,
            dtype="int16",
            blocksize=CHUNK_SIZE,
            callback=callback,
        )

        with stream:
            while self._recording:
                await asyncio.sleep(0.04)
                if not has_spoken and total_chunks >= max_listen_chunks:
                    break
                if has_spoken and silent_chunks >= max_silent_chunks:
                    break
                if total_chunks >= max_chunks:
                    break

        self._recording = False
        if not has_spoken or not self._frames:
            return None

        audio_bytes = b"".join(self._frames)
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

        # 1. Forward audio to connected Companion apps (PC / Mobile)
        try:
            import base64

            from jarvis.server.companion_manager import companion_manager
            if companion_manager.has_companions():
                with open(str(filepath), "rb") as f:
                    audio_b64 = base64.b64encode(f.read()).decode("utf-8")
                fmt = filepath.suffix.lstrip(".").lower() or "mp3"
                asyncio.create_task(
                    companion_manager.broadcast_command(
                        action="play_audio",
                        params={"audio_base64": audio_b64, "format": fmt}
                    )
                )
        except Exception as e:
            logger.debug("audio_player.companion_broadcast_skipped", error=str(e))

        # 2. Local soundcard playback fallback
        suffix = filepath.suffix.lower()
        if suffix == ".wav":
            try:
                import numpy as np
                import sounddevice as sd

                with wave.open(str(filepath), "rb") as wf:
                    frames = wf.readframes(wf.getnframes())
                    sample_rate = wf.getframerate()
                    channels = wf.getnchannels()
                    sample_width = wf.getsampwidth()

                dtype = {1: "int8", 2: "int16", 4: "int32"}.get(sample_width, "int16")
                audio = np.frombuffer(frames, dtype=dtype)
                if channels > 1:
                    audio = audio.reshape(-1, channels)

                sd.play(audio, samplerate=sample_rate, blocking=False)
                sd.wait()
                return
            except Exception as exc:
                logger.debug("audio.wav_local_play_fallback", error=str(exc))

        # System command playback fallback
        import platform
        import subprocess

        system = platform.system()
        try:
            if system == "Windows":
                if suffix == ".wav":
                    ps_cmd = f"(New-Object Media.SoundPlayer '{filepath}').PlaySync()"
                    subprocess.Popen(
                        ["powershell", "-c", ps_cmd],
                        stdout=subprocess.DEVNULL,
                        stderr=subprocess.DEVNULL,
                    )
                else:
                    cmd = (
                        f"$wmp = New-Object -ComObject WMPlayer.OCX; "
                        f"$wmp.URL = '{filepath}'; "
                        f"$wmp.controls.play(); "
                        f"Start-Sleep -Seconds 2"
                    )
                    subprocess.Popen(
                        ["powershell", "-c", cmd],
                        stdout=subprocess.DEVNULL,
                        stderr=subprocess.DEVNULL,
                    )
            elif system == "Darwin":
                subprocess.Popen(
                    ["afplay", str(filepath)],
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL,
                )
            else:
                subprocess.Popen(
                    ["ffplay", "-nodisp", "-autoexit", "-loglevel", "quiet", str(filepath)],
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL,
                )
        except Exception as e:
            logger.debug("audio.system_playback_failed", error=str(e))

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
