from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any


@dataclass(slots=True)
class LiveEvent:
    """
    Formato interno da aplicação.

    A camada do TikTok converte o evento externo para este formato.
    O restante do sistema não precisa saber qual API gerou o evento.
    """
    type: str
    username: str = ""
    display_name: str = ""
    text: str = ""
    gift_name: str = ""
    gift_id: str | None = None
    quantity: int = 1
    like_count: int = 0
    raw: Any = None
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))

    def actor(self) -> str:
        return self.display_name or self.username or "desconhecido"
