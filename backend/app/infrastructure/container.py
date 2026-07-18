"""Composition-root container: declarative adapter-to-port bindings (ADR-0009).

All concrete adapters are bound to their ports here, in one place. Routers inject
providers via ``Provide[Container.<name>]``; that router-to-container import is the
one sanctioned exception to the inward dependency rule (ADR-0005/ADR-0009).
"""

from dependency_injector import containers

# Router modules whose ``Provide`` markers the container resolves at startup. Add a
# module here as soon as one of its routes injects a provider; /health needs none.
WIRED_MODULES: list[str] = []


class Container(containers.DeclarativeContainer):
    """Application container holding every adapter-to-port binding.

    Providers are resolved into the wired router modules at startup. Swap a
    binding here to repoint the whole graph; tests override providers on an
    instance rather than patching call sites.

    No adapters are bound yet: the only route, /health, has no dependencies.
    """

    wiring_config = containers.WiringConfiguration(modules=WIRED_MODULES)
