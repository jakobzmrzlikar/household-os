"""Mock of the speech transcription port returning a fixed transcript."""

from attrs import define, field

from app.domain.ports.speech_transcription import (
    SpeechTranscriptionPort,
    SpeechTranscriptionRequest,
)

TRANSCRIPT = "we are out of olive oil and milk"


@define
class MockSpeechTranscription(SpeechTranscriptionPort):
    """Transcription answering every request with a fixed voice-note transcript."""

    transcript: str = TRANSCRIPT
    requests: list[SpeechTranscriptionRequest] = field(factory=list)

    async def transcribe(self, request: SpeechTranscriptionRequest) -> str:
        """Record the request and return the canned transcript.

        :param request: The audio bytes and content type of the recording.
        :return: The fixed transcript.
        """
        self.requests.append(request)
        return self.transcript
