from typing import TypedDict, Literal

class RealtimeSTTHandshake(TypedDict, total=False):
    # REQUIRED
    model_id: str
    # e.g. "scribe_v2_realtime"

    # AUTHENTICATION (one of these)
    token: str
    # Temporary client token (recommended for browsers)

    # AUDIO CONFIG
    audio_format: Literal[
        "pcm_16000",
        "pcm_44100",
        "pcm_48000"
    ]
    # Default: "pcm_16000"

    sample_rate: int
    # Usually implied by audio_format, but allowed explicitly

    # LANGUAGE
    language_code: str
    # ISO 639-1 or 639-3 (e.g. "en", "en-US", "fr")

    include_language_detection: bool
    # If true, response includes detected language

    # TRANSCRIPT OPTIONS
    include_timestamps: bool
    # Enables word-level timestamps

    # CONTEXT
    previous_text: str
    # Optional prior transcript context

    # COMMIT STRATEGY
    commit_strategy: Literal["manual", "vad"]
    # Default: "manual"

class RealtimeSTTVADConfig(TypedDict, total=False):
    vad_threshold: float
    # Speech probability threshold (0.0–1.0)

    vad_silence_threshold_secs: float
    # Silence duration to trigger commit

    min_speech_duration_ms: int
    # Minimum speech length before commit

    min_silence_duration_ms: int
    # Minimum silence length before commit

class HandshakeOpts(
    RealtimeSTTHandshake,
    RealtimeSTTVADConfig,
    total=False
):
    ...
