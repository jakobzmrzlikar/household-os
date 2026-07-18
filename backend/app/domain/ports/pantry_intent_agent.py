"""Driven port for extracting structured pantry intents from a transcript."""

from typing import Protocol, runtime_checkable

from attrs import define

from app.domain.models.pantry_intent import PantryIntent
from app.domain.models.pending_command import Provenance


@runtime_checkable
class PantryIntentAgentPort(Protocol):
    """Port for turning a voice-note transcript into structured pantry intents."""

    async def extract_intents(
        self, request: "PantryIntentExtractionRequest"
    ) -> "PantryIntentExtractionResponse":
        """Extract pantry intents from a voice-note transcript.

        :param request: The transcript to extract intents from.
        :return: Zero or more pantry intents and the provenance of the
            extraction, transcript included.
        :raises ValueError: When the extracted data violates intent invariants.
        """
        ...


@define
class PantryIntentExtractionRequest:
    """A voice-note transcript to extract pantry intents from.

    :param transcript: Plain-text transcript of the voice note.
    """

    transcript: str


@define
class PantryIntentExtractionResponse:
    """The outcome of a pantry intent extraction.

    :param intents: The pantry intents heard in the transcript; may be empty.
    :param provenance: Which agent and model produced the extraction, carrying
        the transcript for the approval UI.
    """

    intents: tuple[PantryIntent, ...]
    provenance: Provenance
