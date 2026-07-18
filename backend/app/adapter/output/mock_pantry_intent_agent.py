"""Mock of the pantry intent agent port returning fixed out-of-stock intents."""

from attrs import define, field

from app.domain.models.pantry_intent import PantryIntent
from app.domain.models.pending_command import Provenance
from app.domain.ports.pantry_intent_agent import (
    PantryIntentAgentPort,
    PantryIntentExtractionRequest,
    PantryIntentExtractionResponse,
)

AGENT_NAME = "mock_pantry_intent_agent"
MODEL_ID = "mock"

_OUT_OF_STOCK_INTENTS = (
    PantryIntent(name="Olive oil", out_of_stock=True),
    PantryIntent(name="Milk", out_of_stock=True),
)


@define
class MockPantryIntentAgent(PantryIntentAgentPort):
    """Intent agent answering every transcript with fixed out-of-stock intents."""

    intents: tuple[PantryIntent, ...] = _OUT_OF_STOCK_INTENTS
    requests: list[PantryIntentExtractionRequest] = field(factory=list)

    async def extract_intents(
        self, request: PantryIntentExtractionRequest
    ) -> PantryIntentExtractionResponse:
        """Record the request and return the canned intents.

        :param request: The transcript to extract intents from.
        :return: The fixed intents with mock provenance carrying the transcript.
        """
        self.requests.append(request)
        return PantryIntentExtractionResponse(
            intents=self.intents,
            provenance=Provenance(
                agent_name=AGENT_NAME,
                model_id=MODEL_ID,
                transcript=request.transcript,
            ),
        )
