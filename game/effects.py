import time
from dataclasses import dataclass
from typing import Callable

FADE = 0.6


@dataclass
class Announcement:
    """Um aviso para a tela: presente, follow, level up, evento especial."""

    kind: str
    actor: str
    text: str
    detail: str = ""
    icon: str = ""
    big: bool = False
    ttl: float = 4.0
    created: float = 0.0

    def age(self, now: float) -> float:
        return now - self.created

    def alpha(self, now: float) -> float:
        """Desaparece suavemente no ultimo trecho de vida."""
        if self.ttl <= 0:
            return 0.0
        restante = self.ttl - self.age(now)
        if restante <= 0:
            return 0.0
        if restante >= FADE:
            return 1.0
        return restante / FADE


class EffectSet:
    """Efeitos temporarios com prazo de validade.

    Reativar um efeito pega o MAIOR fim, nao soma as duracoes: dois
    escudos de 5s dao 5s, nao 10s.
    """

    def __init__(self, now_fn: Callable[[], float] = time.monotonic):
        self._now = now_fn
        self._fins: dict[str, float] = {}

    def activate(self, name: str, duration: float) -> None:
        if duration <= 0:
            return
        fim = self._now() + duration
        self._fins[name] = max(self._fins.get(name, 0.0), fim)

    def active(self, name: str) -> bool:
        return self._fins.get(name, 0.0) > self._now()

    def remaining(self, name: str) -> float:
        return max(0.0, self._fins.get(name, 0.0) - self._now())

    def expire(self) -> None:
        agora = self._now()
        self._fins = {k: v for k, v in self._fins.items() if v > agora}

    def active_names(self) -> list[str]:
        agora = self._now()
        return [k for k, v in self._fins.items() if v > agora]


class AnnouncementQueue:
    """Fila de avisos exibidos na tela.

    Pertence ao jogo, nao ao renderer: qualquer renderer futuro mostra os
    mesmos avisos lendo este estado.
    """

    def __init__(
        self,
        now_fn: Callable[[], float] = time.monotonic,
        max_size: int = 8,
    ):
        self._now = now_fn
        self._max = max(1, max_size)
        self._itens: list[Announcement] = []

    def push(
        self,
        kind: str,
        actor: str,
        text: str,
        detail: str = "",
        icon: str = "",
        ttl: float = 4.0,
        big: bool = False,
    ) -> Announcement:
        agora = self._now()
        item = Announcement(
            kind=kind,
            actor=actor,
            text=text,
            detail=detail,
            icon=icon,
            big=big,
            ttl=ttl,
            created=agora,
        )
        self._itens.append(item)
        self._expirar(agora)
        # Corta os mais antigos, mantendo os mais recentes.
        if len(self._itens) > self._max:
            self._itens = self._itens[-self._max :]
        return item

    def _expirar(self, agora: float) -> None:
        self._itens = [a for a in self._itens if a.age(agora) < a.ttl]

    def active(self) -> list[Announcement]:
        self._expirar(self._now())
        return list(self._itens)

    def expire(self) -> None:
        self._expirar(self._now())
