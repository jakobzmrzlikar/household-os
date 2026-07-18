"""FastAPI router for the list_pending_commands query."""

from dependency_injector.wiring import Provide, inject
from fastapi import APIRouter, Depends, HTTPException, Query, status

from app.adapter.input.web.models.pending_command import (
    ApiListPendingCommandsResponse,
    ApiPendingCommand,
)
from app.application.list_pending_commands import (
    ListPendingCommandsRequest,
    ListPendingCommandsUsecase,
)
from app.infrastructure.container import Container

router = APIRouter()


@router.get("/list_pending_commands")
@inject
async def list_pending_commands(
    household_id: str = Query(),
    list_pending_commands_usecase: ListPendingCommandsUsecase = Depends(
        Provide[Container.list_pending_commands_usecase]
    ),
) -> ApiListPendingCommandsResponse:
    """List a household's staged commands awaiting approval.

    :param household_id: Household whose pending commands to list.
    :param list_pending_commands_usecase: Injected use case executing the query.
    :return: The pending commands with their human-readable summaries.
    :raises HTTPException: 422 when ``household_id`` is blank.
    """
    try:
        commands = await list_pending_commands_usecase(
            ListPendingCommandsRequest(household_id=household_id)
        )
    except ValueError as error:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT, detail=str(error)
        ) from error
    return ApiListPendingCommandsResponse(
        commands=[ApiPendingCommand.from_domain(command) for command in commands]
    )
