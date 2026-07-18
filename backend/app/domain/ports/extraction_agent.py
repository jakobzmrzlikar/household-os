"""Driven port for extracting structured receipts from capture images."""

from typing import Protocol, runtime_checkable

from attrs import define

from app.domain.models.pending_command import Provenance
from app.domain.models.receipt import Receipt


@runtime_checkable
class ExtractionAgentPort(Protocol):
    """Port for turning a captured receipt photo into structured receipt data."""

    async def extract_receipt(
        self, request: "ReceiptExtractionRequest"
    ) -> "ReceiptExtractionResponse":
        """Extract a structured receipt from a receipt photo.

        :param request: The image bytes and media type of the receipt photo.
        :return: The extracted receipt and the provenance of the extraction.
        :raises ValueError: When the extracted data violates receipt invariants.
        """
        ...


@define
class ReceiptExtractionRequest:
    """A receipt photo to extract.

    :param image: Raw bytes of the receipt photo.
    :param media_type: MIME type of the image (e.g. ``image/jpeg``).
    """

    image: bytes
    media_type: str


@define
class ReceiptExtractionResponse:
    """The outcome of a receipt extraction.

    :param receipt: The structured receipt read from the photo.
    :param provenance: Which agent and model produced the extraction.
    """

    receipt: Receipt
    provenance: Provenance
