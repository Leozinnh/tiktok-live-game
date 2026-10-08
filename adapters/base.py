from dataclasses import dataclass
from typing import Protocol, runtime_checkable


@dataclass
class AdapterStatus:
    """Estado da conexao, exibido no HUD."""

    connected: bool = False
    detail: str = "desconectado"
    reconnects: int = 0


@runtime_checkable
class LiveAdapter(Protocol):
    """Fonte de eventos.

    Implementado por `TikTokLiveAdapter` (LIVE real) e `SimulatedAdapter`
    (modo teste). O resto do sistema nao sabe qual dos dois esta ativo:
    ambos escrevem na mesma `EventQueue`.
    """

    def start(self) -> None: ...

    def stop(self) -> None: ...

    @property
    def status(self) -> AdapterStatus: ...
