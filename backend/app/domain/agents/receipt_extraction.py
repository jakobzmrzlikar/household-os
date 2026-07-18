"""Receipt extraction agent: reads a receipt photo into structured receipt data."""

from attrs import define, field
from pydantic import BaseModel, Field
from pydantic_ai import Agent, BinaryImage
from pydantic_ai.models import Model

from app.domain.models.pending_command import Provenance
from app.domain.models.receipt import Receipt, ReceiptLineItem
from app.domain.ports.extraction_agent import (
    ExtractionAgentPort,
    ReceiptExtractionRequest,
    ReceiptExtractionResponse,
)

AGENT_NAME = "receipt_extraction"

_INSTRUCTIONS = (
    "You extract structured data from photos of shopping receipts. "
    "Read the receipt image and return the merchant name, the grand total, "
    "the ISO 4217 currency code, and every line item with its quantity, "
    "unit, and line price. Use only values printed on the receipt; "
    "do not invent items."
)


class ExtractedLineItem(BaseModel):
    """One purchased line item, as returned by the model (boundary output)."""

    name: str = Field(description="Product name as printed on the receipt.")
    quantity: float = Field(ge=0, description="Purchased quantity, in `unit`.")
    unit: str = Field(description="Unit of measure, e.g. 'pcs', 'kg', 'l'.")
    price: float = Field(
        ge=0, description="Total price of the line in the receipt currency."
    )


class ExtractedReceipt(BaseModel):
    """A structured receipt, as returned by the model (boundary output)."""

    merchant: str = Field(description="Name of the merchant that issued the receipt.")
    total: float = Field(ge=0, description="Grand total of the receipt.")
    currency: str = Field(description="ISO 4217 currency code of the amounts.")
    line_items: list[ExtractedLineItem]


@define(kw_only=True)
class ReceiptExtractionAgent(ExtractionAgentPort):
    """Extraction agent backed by a Pydantic AI vision agent.

    The concrete model is injected from the composition root, either as a
    ``provider:model`` identifier string or as an already-bound model object
    carrying its credentials; this module never names a provider.
    """

    model: str | Model
    _agent: Agent[object, ExtractedReceipt] = field(init=False, repr=False)

    def __attrs_post_init__(self) -> None:
        # defer_model_check: resolving an identifier string eagerly requires
        # the provider's API key at construction, which would fail requests
        # (e.g. a 404 for an unknown capture) that never reach the model.
        # Defer so the key is only needed when an extraction actually runs.
        self._agent = Agent(
            self.model,
            name=AGENT_NAME,
            output_type=ExtractedReceipt,
            instructions=_INSTRUCTIONS,
            defer_model_check=True,
        )

    @property
    def _model_id(self) -> str:
        """Qualified ``provider:model`` identifier of the bound model."""
        if isinstance(self.model, str):
            return self.model
        return f"{self.model.system}:{self.model.model_name}"

    async def extract_receipt(
        self, request: ReceiptExtractionRequest
    ) -> ReceiptExtractionResponse:
        """Run the vision agent on a receipt photo.

        :param request: The image bytes and media type of the receipt photo.
        :return: The extracted receipt and this agent's provenance.
        :raises ValueError: When the extracted data violates receipt invariants.
        """
        result = await self._agent.run(
            [
                "Extract the structured receipt from this photo.",
                BinaryImage(data=request.image, media_type=request.media_type),
            ]
        )
        return ReceiptExtractionResponse(
            receipt=_to_domain(result.output),
            provenance=Provenance(agent_name=AGENT_NAME, model_id=self._model_id),
        )


def _to_domain(extracted: ExtractedReceipt) -> Receipt:
    """Map the model's boundary output to the domain receipt.

    :param extracted: The validated structured output of the agent run.
    :return: The domain receipt value object.
    :raises ValueError: When an amount or quantity is negative.
    """
    return Receipt(
        merchant=extracted.merchant,
        total=extracted.total,
        currency=extracted.currency,
        line_items=tuple(
            ReceiptLineItem(
                name=item.name,
                quantity=item.quantity,
                unit=item.unit,
                price=item.price,
            )
            for item in extracted.line_items
        ),
    )
