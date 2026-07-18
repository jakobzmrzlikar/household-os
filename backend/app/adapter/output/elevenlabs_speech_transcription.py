"""ElevenLabs Scribe implementation of the speech transcription port."""

from attrs import define, field
from elevenlabs import AsyncElevenLabs
from elevenlabs.core.api_error import ApiError
from elevenlabs.types import SpeechToTextChunkResponseModel

from app.domain.ports.speech_transcription import (
    SpeechTranscriptionError,
    SpeechTranscriptionPort,
    SpeechTranscriptionRequest,
)

MODEL_ID = "scribe_v2"


@define(kw_only=True)
class ElevenLabsSpeechTranscription(SpeechTranscriptionPort):
    """Transcription adapter calling the ElevenLabs speech-to-text (Scribe) API."""

    api_key: str | None
    model_id: str = MODEL_ID
    _client: AsyncElevenLabs = field(init=False, repr=False)

    def __attrs_post_init__(self) -> None:
        # The SDK also reads ELEVENLABS_API_KEY from the process environment,
        # but settings are the source of truth here (uvicorn does not populate
        # the environment from backend/.env).
        self._client = AsyncElevenLabs(api_key=self.api_key)

    async def transcribe(self, request: SpeechTranscriptionRequest) -> str:
        """Transcribe a voice recording with the Scribe model.

        :param request: The audio bytes and content type of the recording.
        :return: The plain-text transcript of the recording.
        :raises SpeechTranscriptionError: When the API call fails or answers
            with something other than a single-channel transcript.
        """
        try:
            result = await self._client.speech_to_text.convert(
                file=("voice-note", request.audio, request.content_type),
                model_id=self.model_id,
            )
        except ApiError as error:
            raise SpeechTranscriptionError(
                f"ElevenLabs transcription failed: {error}"
            ) from error
        # convert() is typed as a union: multi-channel and webhook responses
        # carry no plain transcript, but both only occur for request options
        # this adapter never sets.
        if not isinstance(result, SpeechToTextChunkResponseModel):
            raise SpeechTranscriptionError(
                f"Unexpected transcription response: {type(result).__name__}"
            )
        return result.text
