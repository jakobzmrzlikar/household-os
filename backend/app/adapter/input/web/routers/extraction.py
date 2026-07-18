"""FastAPI router for the run_extraction command."""

from dependency_injector.wiring import Provide, inject
from fastapi import APIRouter, Depends, HTTPException, status

from app.adapter.input.web.models.extraction import (
    ApiRunExtractionRequest,
    ApiRunExtractionResponse,
)
from app.adapter.input.web.models.pending_command import ApiPendingCommand
from app.application.run_extraction import (
    CaptureNotExtractableError,
    CaptureNotFoundError,
    RunExtractionRequest,
    RunExtractionUsecase,
)
from app.infrastructure.container import Container

router = APIRouter()


@router.post("/run_extraction", status_code=status.HTTP_201_CREATED)
@inject
async def run_extraction(
    body: ApiRunExtractionRequest,
    run_extraction_usecase: RunExtractionUsecase = Depends(
        Provide[Container.run_extraction_usecase]
    ),
) -> ApiRunExtractionResponse:
    """Run receipt extraction on a capture and stage the proposed commands.

    :param body: The capture to extract.
    :param run_extraction_usecase: Injected use case executing the command.
    :return: The staged pending commands, expense first.
    :raises HTTPException: 404 for an unknown capture, 415 for a non-photo
        capture, 422 for a blank id or an invalid extracted receipt.
    """
    try:
        commands = await run_extraction_usecase(
            RunExtractionRequest(capture_id=body.capture_id)
        )
    except CaptureNotFoundError as error:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail=str(error)
        ) from error
    except CaptureNotExtractableError as error:
        raise HTTPException(
            status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE, detail=str(error)
        ) from error
    except ValueError as error:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT, detail=str(error)
        ) from error
    return ApiRunExtractionResponse(
        commands=[ApiPendingCommand.from_domain(command) for command in commands]
    )
