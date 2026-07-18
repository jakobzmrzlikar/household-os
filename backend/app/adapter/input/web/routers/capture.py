"""FastAPI router for the create_capture command."""

from dependency_injector.wiring import Provide, inject
from fastapi import APIRouter, Depends, Form, HTTPException, UploadFile, status

from app.adapter.input.web.models.capture import ApiCaptureResponse
from app.application.create_capture import CreateCaptureRequest, CreateCaptureUsecase
from app.domain.models.capture import UnsupportedMediaTypeError
from app.infrastructure.container import Container

router = APIRouter()


@router.post("/create_capture", status_code=status.HTTP_201_CREATED)
@inject
async def create_capture(
    file: UploadFile,
    household_id: str = Form(),
    member_id: str = Form(),
    create_capture_usecase: CreateCaptureUsecase = Depends(
        Provide[Container.create_capture_usecase]
    ),
) -> ApiCaptureResponse:
    """Store an uploaded photo or voice note as a new capture.

    :param file: The uploaded photo or audio file (multipart part named ``file``).
    :param household_id: Household the capture belongs to.
    :param member_id: Member who submitted the capture.
    :param create_capture_usecase: Injected use case executing the command.
    :return: The created capture's id and kind.
    :raises HTTPException: 415 for non image/audio uploads, 422 for blank fields
        or empty files.
    """
    content = await file.read()
    try:
        request = CreateCaptureRequest(
            household_id=household_id,
            member_id=member_id,
            content=content,
            filename=file.filename or "upload",
            content_type=file.content_type or "",
        )
        capture = await create_capture_usecase(request)
    except UnsupportedMediaTypeError as error:
        raise HTTPException(
            status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
            detail=f"Unsupported content type: {error}",
        ) from error
    except ValueError as error:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail=str(error),
        ) from error
    return ApiCaptureResponse(id=capture.id, kind=capture.kind)
