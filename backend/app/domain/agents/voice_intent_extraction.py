"""Voice intent extraction agent: reads a voice-note transcript into pantry intents."""

from attrs import define, field
from pydantic import BaseModel, Field
from pydantic_ai import Agent
from pydantic_ai.models import Model

from app.domain.models.pantry_intent import PantryIntent
from app.domain.models.pending_command import Provenance
from app.domain.ports.pantry_intent_agent import (
    PantryIntentAgentPort,
    PantryIntentExtractionRequest,
    PantryIntentExtractionResponse,
)

AGENT_NAME = "voice_intent_extraction"

_INSTRUCTIONS = (
    "You extract pantry intents from the transcript of a household voice note. "
    "Return one intent per pantry item the speaker mentions: the item name, "
    "and either a signed quantity change (positive for restocked, negative "
    "for used up) or the out-of-stock flag when the speaker says the item is "
    "gone, finished, or ran out. Never set both. Carry any extra remark about "
    "the item as its note. Ignore everything that is not about pantry stock; "
    "return an empty list when the note mentions no pantry items. Do not "
    "invent items."
)


class ExtractedPantryIntent(BaseModel):
    """One pantry intent, as returned by the model (boundary output)."""

    name: str = Field(description="Name of the pantry item the speaker mentioned.")
    quantity_delta: float | None = Field(
        default=None,
        description=(
            "Signed stock change the speaker stated (negative for consumption). "
            "Omit when the item was declared out of stock."
        ),
    )
    out_of_stock: bool = Field(
        default=False,
        description=(
            "True when the speaker said the item is gone or ran out. "
            "Mutually exclusive with quantity_delta."
        ),
    )
    note: str | None = Field(
        default=None, description="Extra remark the speaker made about the item."
    )


class ExtractedPantryIntents(BaseModel):
    """All pantry intents heard in a transcript (boundary output)."""

    intents: list[ExtractedPantryIntent]


@define(kw_only=True)
class VoiceIntentExtractionAgent(PantryIntentAgentPort):
    """Intent extraction agent backed by a Pydantic AI agent.

    The concrete model is injected from the composition root, either as a
    ``provider:model`` identifier string or as an already-bound model object
    carrying its credentials; this module never names a provider.
    """

    model: str | Model
    _agent: Agent[object, ExtractedPantryIntents] = field(init=False, repr=False)

    def __attrs_post_init__(self) -> None:
        # defer_model_check: resolving an identifier string eagerly requires
        # the provider's API key at construction, which would fail requests
        # that never reach the model. Defer so the key is only needed when an
        # extraction actually runs.
        self._agent = Agent(
            self.model,
            name=AGENT_NAME,
            output_type=ExtractedPantryIntents,
            instructions=_INSTRUCTIONS,
            defer_model_check=True,
        )

    @property
    def _model_id(self) -> str:
        """Qualified ``provider:model`` identifier of the bound model."""
        if isinstance(self.model, str):
            return self.model
        return f"{self.model.system}:{self.model.model_name}"

    async def extract_intents(
        self, request: PantryIntentExtractionRequest
    ) -> PantryIntentExtractionResponse:
        """Run the agent on a voice-note transcript.

        :param request: The transcript to extract intents from.
        :return: The extracted intents and this agent's provenance, transcript
            included.
        :raises ValueError: When the extracted data violates intent invariants.
        """
        result = await self._agent.run(
            "Extract the pantry intents from this voice note transcript:\n\n"
            + request.transcript
        )
        return PantryIntentExtractionResponse(
            intents=tuple(_to_domain(intent) for intent in result.output.intents),
            provenance=Provenance(
                agent_name=AGENT_NAME,
                model_id=self._model_id,
                transcript=request.transcript,
            ),
        )


def _to_domain(extracted: ExtractedPantryIntent) -> PantryIntent:
    """Map the model's boundary output to the domain pantry intent.

    :param extracted: One validated intent from the agent run.
    :return: The domain pantry intent value object.
    :raises ValueError: When the intent carries no stock signal or both.
    """
    return PantryIntent(
        name=extracted.name,
        quantity_delta=extracted.quantity_delta,
        out_of_stock=extracted.out_of_stock,
        note=extracted.note,
    )
