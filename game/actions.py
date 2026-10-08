"""Registro de acoes do jogo.

Cada acao aqui registrada vira um nome valido no campo `action` do
config.json. Este modulo NAO importa `game.engine` em tempo de execucao:
`core.config` importa `known_actions()` daqui para validar a configuracao,
e um import de volta ao engine criaria um ciclo.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Callable

if TYPE_CHECKING:
    from core.events import LiveEvent
    from game.engine import GameEngine

ActionHandler = Callable[["GameEngine", dict, "LiveEvent"], None]

ACTION_REGISTRY: dict[str, ActionHandler] = {}

ANUNCIO_TTL = 4.0


def register(name: str) -> Callable[[ActionHandler], ActionHandler]:
    """Decorator: torna uma funcao uma acao configuravel no config.json."""

    def deco(fn: ActionHandler) -> ActionHandler:
        ACTION_REGISTRY[name] = fn
        return fn

    return deco


def known_actions() -> frozenset[str]:
    return frozenset(ACTION_REGISTRY)


def _anunciar(
    engine: GameEngine, event: LiveEvent, texto: str, detalhe: str = ""
) -> None:
    """Empurra um aviso na tela, se houver um autor identificado."""
    ator = event.actor()
    if not ator or ator == "desconhecido":
        return
    engine.state.announcements.push(
        kind=event.type.value,
        actor=ator,
        text=texto,
        detail=detalhe,
        ttl=ANUNCIO_TTL,
    )


@register("xp")
def _acao_xp(engine: GameEngine, payload: dict, event: LiveEvent) -> None:
    valor = int(payload.get("xp", 0))
    engine.add_xp(valor)
    _anunciar(engine, event, "ganhou XP", f"+{valor} XP")


@register("heal")
def _acao_heal(engine: GameEngine, payload: dict, event: LiveEvent) -> None:
    curado = engine.heal(int(payload.get("amount", 10)))
    _anunciar(engine, event, "curou o personagem", f"+{curado} HP")


@register("damage")
def _acao_damage(engine: GameEngine, payload: dict, event: LiveEvent) -> None:
    valor = int(payload.get("amount", 5))
    engine.damage(valor)
    _anunciar(engine, event, "causou dano", f"-{valor} HP")


@register("run")
def _acao_run(engine: GameEngine, payload: dict, event: LiveEvent) -> None:
    engine.state.effects.activate("run", float(payload.get("duration", 3)))
    _anunciar(engine, event, "fez o personagem CORRER")


@register("jump")
def _acao_jump(engine: GameEngine, payload: dict, event: LiveEvent) -> None:
    engine.state.effects.activate("jump", float(payload.get("duration", 0.8)))
    _anunciar(engine, event, "fez o personagem PULAR")


@register("speed")
def _acao_speed(engine: GameEngine, payload: dict, event: LiveEvent) -> None:
    ganho = float(payload.get("amount", 60))
    duracao = float(payload.get("duration", 5))
    engine.grant_speed(ganho, duracao)
    _anunciar(engine, event, "acelerou", f"+{ganho:.0f}")


@register("shield")
def _acao_shield(engine: GameEngine, payload: dict, event: LiveEvent) -> None:
    engine.state.effects.activate("shield", float(payload.get("duration", 5)))
    _anunciar(engine, event, "ativou ESCUDO")


@register("rage")
def _acao_rage(engine: GameEngine, payload: dict, event: LiveEvent) -> None:
    engine.state.effects.activate("rage", float(payload.get("duration", 8)))
    _anunciar(engine, event, "ativou FÚRIA")


@register("spawn_enemy")
def _acao_spawn_enemy(engine: GameEngine, payload: dict, event: LiveEvent) -> None:
    criados = engine.spawn_enemy(int(payload.get("amount", 1)))
    if criados:
        _anunciar(engine, event, "invocou inimigos", f"+{criados}")


@register("special")
def _acao_special(engine: GameEngine, payload: dict, event: LiveEvent) -> None:
    engine.state.effects.activate("special", float(payload.get("duration", 5)))
    engine.state.announcements.push(
        kind="special",
        actor=event.actor(),
        text="EVENTO ESPECIAL",
        detail=f"{event.actor()} ativou!",
        ttl=5.0,
        big=True,
    )


@register("boss")
def _acao_boss(engine: GameEngine, payload: dict, event: LiveEvent) -> None:
    engine.spawn_boss()


@register("mega")
def _acao_mega(engine: GameEngine, payload: dict, event: LiveEvent) -> None:
    duracao = float(payload.get("duration", 10))
    engine.state.effects.activate("mega", duracao)
    engine.state.effects.activate("shield", duracao)
    engine.add_xp(int(payload.get("xp", 100)))
    engine.state.announcements.push(
        kind="mega",
        actor=event.actor(),
        text="MEGA EVENTO",
        detail=f"{event.actor()} ativou!",
        ttl=6.0,
        big=True,
    )
