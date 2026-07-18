"""Composition-root container: declarative adapter-to-port bindings (ADR-0009).

All concrete adapters are bound to their ports here, in one place. Routers inject
providers via ``Provide[Container.<name>]``; that router-to-container import is the
one sanctioned exception to the inward dependency rule (ADR-0005/ADR-0009).
"""

from dependency_injector import containers, providers

from app.adapter.output.local_disk_media_storage import LocalDiskMediaStorage
from app.adapter.output.sqlalchemy_capture_repository import SqlAlchemyCaptureRepository
from app.application.create_capture import CreateCaptureUsecase
from app.infrastructure.database import create_engine, create_session_factory
from app.infrastructure.settings import Settings

# Router modules whose ``Provide`` markers the container resolves at startup. Add a
# module here as soon as one of its routes injects a provider; /health needs none.
WIRED_MODULES: list[str] = ["app.adapter.input.web.routers.capture"]


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

    create_capture_usecase = providers.Factory(
        CreateCaptureUsecase,
        media_storage=media_storage,
        capture_repository=capture_repository,
    )
