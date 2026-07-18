"""FastAPI router for the pending command endpoints (list, approve, reject)."""

from dependency_injector.wiring import Provide, inject
from fastapi import APIRouter, Depends, HTTPException, Query, status

from app.adapter.input.web.models.pending_command import (
    ApiApproveCommandRequest,
    ApiCommandDecisionResponse,
    ApiListPendingCommandsResponse,
    ApiPendingCommand,
    ApiRejectCommandRequest,
)
from app.application.approve_command import (
    ApproveCommandRequest,
    ApproveCommandUsecase,
    CommandNotFoundError,
)
from app.application.execute_verb import InvalidCommandError
from app.application.list_pending_commands import (
    ListPendingCommandsRequest,
    ListPendingCommandsUsecase,
)
from app.application.reject_command import RejectCommandRequest, RejectCommandUsecase
from app.domain.models.pending_command import CommandNotPendingError
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


@router.post("/approve_command")
@inject
async def approve_command(
    body: ApiApproveCommandRequest,
    approve_command_usecase: ApproveCommandUsecase = Depends(
        Provide[Container.approve_command_usecase]
    ),
) -> ApiCommandDecisionResponse:
    """Approve a staged command: revalidate and execute its verb exactly once.

    :param body: The command to approve and the approving member.
    :param approve_command_usecase: Injected use case executing the command.
    :return: The approved command.
    :raises HTTPException: 404 for an unknown command; 409 when the command
        was already decided or fails revalidation — nothing executed, the
        detail carries the reason; 422 for blank ids.
    """
    try:
        command = await approve_command_usecase(
            ApproveCommandRequest(command_id=body.command_id, member_id=body.member_id)
        )
    except CommandNotFoundError as error:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail=str(error)
        ) from error
    except (CommandNotPendingError, InvalidCommandError) as error:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT, detail=str(error)
        ) from error
    except ValueError as error:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT, detail=str(error)
        ) from error
    return ApiCommandDecisionResponse(command=ApiPendingCommand.from_domain(command))


@router.post("/reject_command")
@inject
async def reject_command(
    body: ApiRejectCommandRequest,
    reject_command_usecase: RejectCommandUsecase = Depends(
        Provide[Container.reject_command_usecase]
    ),
) -> ApiCommandDecisionResponse:
    """Reject a staged command without executing anything.

    :param body: The command to reject and the rejecting member.
    :param reject_command_usecase: Injected use case executing the command.
    :return: The rejected command.
    :raises HTTPException: 404 for an unknown command, 409 when the command
        was already decided, 422 for blank ids.
    """
    try:
        command = await reject_command_usecase(
            RejectCommandRequest(command_id=body.command_id, member_id=body.member_id)
        )
    except CommandNotFoundError as error:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail=str(error)
        ) from error
    except CommandNotPendingError as error:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT, detail=str(error)
        ) from error
    except ValueError as error:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT, detail=str(error)
        ) from error
    return ApiCommandDecisionResponse(command=ApiPendingCommand.from_domain(command))
