"""Mock of the extraction agent port returning a fixed grocery receipt."""

from attrs import define, field

from app.domain.models.pending_command import Provenance
from app.domain.models.receipt import Receipt, ReceiptLineItem
from app.domain.ports.extraction_agent import (
    ExtractionAgentPort,
    ReceiptExtractionRequest,
    ReceiptExtractionResponse,
)

AGENT_NAME = "mock_extraction_agent"
MODEL_ID = "mock"

_GROCERY_RECEIPT = Receipt(
    merchant="Mercator",
    total=23.70,
    currency="EUR",
    line_items=(
        ReceiptLineItem(name="Milk", quantity=2, unit="l", price=2.18),
        ReceiptLineItem(name="Bread", quantity=1, unit="pcs", price=3.20),
        ReceiptLineItem(name="Eggs", quantity=10, unit="pcs", price=4.50),
        ReceiptLineItem(name="Apples", quantity=1.5, unit="kg", price=3.82),
        ReceiptLineItem(name="Coffee", quantity=1, unit="pcs", price=10.00),
    ),
)


@define
class MockExtractionAgent(ExtractionAgentPort):
    """Extraction agent answering every request with a fixed grocery receipt."""

    receipt: Receipt = _GROCERY_RECEIPT
    requests: list[ReceiptExtractionRequest] = field(factory=list)

    async def extract_receipt(
        self, request: ReceiptExtractionRequest
    ) -> ReceiptExtractionResponse:
        """Record the request and return the canned receipt.

        :param request: The image bytes and media type of the receipt photo.
        :return: The fixed grocery receipt with mock provenance.
        """
        self.requests.append(request)
        return ReceiptExtractionResponse(
            receipt=self.receipt,
            provenance=Provenance(agent_name=AGENT_NAME, model_id=MODEL_ID),
        )
