"""FastAPI router for the health-check endpoint."""

from fastapi import APIRouter

router = APIRouter()


@router.get("/health")
def health() -> dict[str, str]:
    """Report service liveness.

    :return: A status payload indicating the service is up.
    """
    return {"status": "ok"}
