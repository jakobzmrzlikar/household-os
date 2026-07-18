"""Composition-root container: declarative adapter-to-port bindings (ADR-0009).

All concrete adapters are bound to their ports here, in one place. Routers inject
providers via ``Provide[Container.<name>]``; that router-to-container import is the
one sanctioned exception to the inward dependency rule (ADR-0005/ADR-0009).
"""

from dependency_injector import containers, providers

from app.adapter.output.local_disk_media_storage import LocalDiskMediaStorage
from app.adapter.output.sqlalchemy_capture_repository import SqlAlchemyCaptureRepository
from app.adapter.output.sqlalchemy_unit_of_work import SqlAlchemyUnitOfWork
from app.application.approve_command import ApproveCommandUsecase
from app.application.create_capture import CreateCaptureUsecase
from app.application.list_pending_commands import ListPendingCommandsUsecase
from app.application.reject_command import RejectCommandUsecase
from app.application.run_extraction import RunExtractionUsecase
from app.domain.agents.receipt_extraction import ReceiptExtractionAgent
from app.infrastructure.database import create_engine, create_session_factory
from app.infrastructure.llm import create_extraction_model
from app.infrastructure.settings import Settings

# Router modules whose ``Provide`` markers the container resolves at startup. Add a
# module here as soon as one of its routes injects a provider; /health needs none.
WIRED_MODULES: list[str] = [
    "app.adapter.input.web.routers.capture",
    "app.adapter.input.web.routers.extraction",
    "app.adapter.input.web.routers.pending_command",
]


class Container(containers.DeclarativeContainer):
    """Application container holding every adapter-to-port binding.

    Providers are resolved into the wired router modules at startup. Swap a
    binding here to repoint the whole graph; tests override providers on an
    instance rather than patching call sites.
    """

    wiring_config = containers.WiringConfiguration(modules=WIRED_MODULES)

    settings = providers.Singleton(Settings)

    engine = providers.Singleton(
        create_engine, database_url=settings.provided.database_url
    )
    session_factory = providers.Singleton(create_session_factory, engine=engine)

    media_storage = providers.Singleton(
        LocalDiskMediaStorage, root_dir=settings.provided.uploads_dir
    )
    capture_repository = providers.Factory(
        SqlAlchemyCaptureRepository, session_factory=session_factory
    )
    # One unit of work per command execution: every use case receives the
    # factory (``.provider``) and opens its own single-transaction scope.
    unit_of_work = providers.Factory(
        SqlAlchemyUnitOfWork, session_factory=session_factory
    )

    # The concrete model binding for the receipt extraction agent lives here,
    # in the composition root, never in the agent module (see CLAUDE.md). The
    # API key flows from settings (backend/.env) because provider SDKs only
    # read the process environment, which uvicorn does not populate from .env.
    extraction_model = providers.Singleton(
        create_extraction_model,
        model_id=settings.provided.extraction_model,
        openai_api_key=settings.provided.openai_api_key,
    )
    extraction_agent = providers.Singleton(
        ReceiptExtractionAgent, model=extraction_model
    )

    run_extraction_usecase = providers.Factory(
        RunExtractionUsecase,
        capture_repository=capture_repository,
        media_storage=media_storage,
        extraction_agent=extraction_agent,
        unit_of_work_factory=unit_of_work.provider,
    )
    create_capture_usecase = providers.Factory(
        CreateCaptureUsecase,
        media_storage=media_storage,
        capture_repository=capture_repository,
        run_extraction_usecase=run_extraction_usecase,
    )
    list_pending_commands_usecase = providers.Factory(
        ListPendingCommandsUsecase,
        unit_of_work_factory=unit_of_work.provider,
    )
    approve_command_usecase = providers.Factory(
        ApproveCommandUsecase,
        unit_of_work_factory=unit_of_work.provider,
    )
    reject_command_usecase = providers.Factory(
        RejectCommandUsecase,
        unit_of_work_factory=unit_of_work.provider,
    )
