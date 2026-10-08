"""Ponto de entrada do jogo interativo para LIVE do TikTok.

Uso:
    python main.py                       # LIVE real, usando o config.json
    python main.py --test                # modo teste: eventos digitados no terminal
    python main.py --test --script demo  # cenario roteirizado
    python main.py --test --burst 500    # rajada aleatoria, para provar o anti-spam
"""

import argparse
import logging
import random
import sys
import time

import pygame

from adapters.base import AdapterStatus
from adapters.simulated import SimulatedAdapter, run_burst
from core.config import ConfigError, load_config
from core.event_queue import EventQueue
from core.events import EventType, LiveEvent
from core.logging_setup import EventJournal, setup_logging
from core.ratelimit import RateLimiter
from core.rules import RuleEngine
from game.engine import GameEngine
from ui.pygame_ui import PygameUI

logger = logging.getLogger("main")


def parse_args(argv=None):
    p = argparse.ArgumentParser(
        prog="main.py",
        description="Jogo interativo para LIVE do TikTok, em 9:16, para captura pelo OBS.",
    )
    p.add_argument("--config", default="config.json", help="caminho do config.json")
    p.add_argument(
        "--test",
        action="store_true",
        help="modo teste: nao conecta ao TikTok, aceita eventos digitados",
    )
    p.add_argument("--script", help="no modo teste, reproduz um cenario (demo, caos, presentes)")
    p.add_argument(
        "--burst",
        type=int,
        metavar="N",
        help="no modo teste, envia N eventos aleatorios de uma vez e sai",
    )
    p.add_argument("--scale", type=float, help="sobrepoe app.render_scale do config")
    p.add_argument("--username", help="sobrepoe tiktok.username do config")
    return p.parse_args(argv)


def build_adapter(args, fila: EventQueue, config: dict):
    """Live real ou simulada. Este e o UNICO ponto que troca a fonte de eventos."""
    if args.test or args.script or args.burst:
        return SimulatedAdapter(fila, config, interactive=not args.script and not args.burst)

    from adapters.tiktok_live import TikTokLiveAdapter

    return TikTokLiveAdapter(fila, config)


def rodar_script(nome: str, fila: EventQueue, config: dict) -> None:
    """Cenarios roteirizados do modo teste."""
    agora = time.monotonic()

    if nome == "presentes":
        for presente in ["Rose", "GG", "Finger Heart", "Ice Cream Cone", "Doughnut"]:
            fila.put(LiveEvent(type=EventType.GIFT, username="joao", gift_name=presente))
    elif nome == "caos":
        run_burst(fila, config, count=500)
    else:  # demo
        roteiro = [
            LiveEvent(type=EventType.SYSTEM, text="connected"),
            LiveEvent(type=EventType.COMMENT, username="maria", text="direita"),
            LiveEvent(type=EventType.GIFT, username="joao", gift_name="Rose"),
            LiveEvent(type=EventType.COMMENT, username="pedro", text="corre"),
            LiveEvent(type=EventType.FOLLOW, username="carlos"),
            LiveEvent(type=EventType.GIFT, username="ana", gift_name="GG"),
            LiveEvent(type=EventType.SHARE, username="lucas"),
            LiveEvent(type=EventType.COMMENT, username="bia", text="esquerda"),
            LiveEvent(type=EventType.LIKE, username="ana", like_delta=100, like_total=100),
            LiveEvent(type=EventType.GIFT, username="joao", gift_name="Confetti"),
            LiveEvent(type=EventType.GIFT, username="maria", gift_name="Cap", quantity=5),
            LiveEvent(type=EventType.LIKE, username="bia", like_delta=200, like_total=300),
            LiveEvent(type=EventType.GIFT, username="pedro", gift_name="TikTok"),
            LiveEvent(type=EventType.COMMENT, username="carlos", text="pula"),
            LiveEvent(type=EventType.GIFT, username="lucas", gift_name="Lion"),
        ]
        for i, evento in enumerate(roteiro):
            fila.put(evento)
            print(f"  [{i + 1}/{len(roteiro)}] {evento.type} {evento.actor()} {evento.gift_name or evento.text}")
    logger.info("Cenario '%s' carregado (%s eventos na fila).", nome, fila.size())


def main(argv=None) -> int:
    args = parse_args(argv)
    setup_logging("logs")
    journal = EventJournal("logs/events.jsonl")

    modo_teste = bool(args.test or args.script or args.burst)

    try:
        # O modo teste nao conecta ao TikTok, entao aceita o config.json
        # recem-clonado, ainda com o placeholder de username. O modo LIVE
        # exige um username de verdade.
        config = load_config(args.config, exigir_username=not modo_teste)
    except ConfigError as erro:
        print(f"\nERRO DE CONFIGURACAO:\n  {erro}\n", file=sys.stderr)
        return 2

    if args.scale is not None:
        config["app"]["render_scale"] = args.scale
    if args.username is not None:
        config["tiktok"]["username"] = args.username

    fila = EventQueue(maxsize=config["app"].get("queue_max_size", 5000))
    game = GameEngine(config)
    limiter = RateLimiter(
        action_budget=config.get("limits", {}).get("action_budget", {}),
    )
    regras = RuleEngine(config, game, limiter, on_event=journal.record)

    if args.burst:
        run_burst(fila, config, count=args.burst)

    ui = PygameUI(config, game)
    adaptador = build_adapter(args, fila, config)

    if args.script:
        rodar_script(args.script, fila, config)

    adaptador.start()
    logger.info(
        "Sistema iniciado | modo=%s | resolucao=%sx%s | escala=%s",
        "TESTE" if (args.test or args.script or args.burst) else "LIVE REAL",
        config["app"]["window_width"],
        config["app"]["window_height"],
        config["app"]["render_scale"],
    )

    clock = pygame.time.Clock()
    fps = config["app"].get("fps", 60)
    por_frame = config["app"].get("events_per_frame", 25)
    rodando = True

    try:
        while rodando:
            dt = clock.tick(fps) / 1000.0
            agora = time.monotonic()

            acoes = ui.poll()
            if "quit" in acoes:
                rodando = False
            if "teste_comentario" in acoes:
                fila.put(LiveEvent(type=EventType.COMMENT, username="tecla", text="direita"))
            if "teste_presente" in acoes:
                fila.put(LiveEvent(type=EventType.GIFT, username="tecla", gift_name="Rose"))
            if "teste_rajada" in acoes:
                run_burst(fila, config, count=200)

            for evento in fila.drain(por_frame):
                regras.process(evento)

            game.update(dt)
            ui.draw(adaptador.status, fila.size(), agora)

    except KeyboardInterrupt:
        logger.info("Interrompido pelo teclado.")
    finally:
        adaptador.stop()
        # Drena o que sobrou para o journal nao perder os ultimos eventos.
        for evento in fila.drain(1000):
            journal.record(evento)
        journal.close()
        ui.close()
        logger.info(
            "Encerrado | aceitos=%s | descartados=%s",
            fila.accepted,
            fila.dropped,
        )

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
