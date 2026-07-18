"""Driven port for transcribing captured voice notes to text."""

from typing import Protocol, runtime_checkable

from attrs import define


@runtime_checkable
class SpeechTranscriptionPort(Protocol):
    """Port for turning a captured audio recording into a text transcript."""

    async def transcribe(self, request: "SpeechTranscriptionRequest") -> str:
        """Transcribe a voice recording to text.

        :param request: The audio bytes and content type of the recording.
        :return: The plain-text transcript of the recording.
        :raises SpeechTranscriptionError: When the transcription provider fails.
        """
        ...


@define
class SpeechTranscriptionRequest:
    """A voice recording to transcribe.

    :param audio: Raw bytes of the audio recording.
    :param content_type: MIME type of the recording (e.g. ``audio/mp4``).
    """

    audio: bytes
    content_type: str


class SpeechTranscriptionError(RuntimeError):
    """Raised when the transcription provider cannot produce a transcript."""
