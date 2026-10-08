"""Ponto de entrada do jogo interativo para LIVE do TikTok.

Uso:
    python main.py                       # LIVE real, usando o config.json
    python main.py --test                # modo teste: eventos digitados no terminal
    python main.py --test --script demo  # cenario roteirizado
    python main.py --test --burst 500    # rajada aleatoria, para provar o anti-spam

Renderers:
    (padrao)      janela do pygame, 2D, capturada por Window Capture
    --web         3D no navegador; o Python nao abre janela nenhuma

Os dois renderers leem o mesmo GameState e o mesmo config.json. Trocar de
um para o outro nao muda regra, presente nem comando.
"""

import argparse
import logging
import random
import sys
import time


from adapters.base import AdapterStatus
from adapters.simulated import SimulatedAdapter, run_burst
from core.config import ConfigError, load_config
from core.event_queue import EventQueue
from core.events import EventType, LiveEvent
from core.logging_setup import EventJournal, setup_logging
from core.ratelimit import RateLimiter
from core.rules import RuleEngine
from game.engine import GameEngine
from renderer_web.servidor import ServidorWeb
from renderer_web.snapshot import snapshot

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
    p.add_argument(
        "--web",
        action="store_true",
        help="renderiza em 3D no navegador em vez de abrir a janela do pygame",
    )
    p.add_argument(
        "--porta",
        type=int,
        default=8765,
        help="porta do renderer web (0 escolhe uma livre)",
    )
    return p.parse_args(argv)


class Relogio:
    """Limita o quadro sem depender do pygame.

    O modo `--web` nao abre janela, entao `pygame.time.Clock()` nao tem
    onde se apoiar. Mesma interface: `tick()` devolve os milissegundos do
    quadro, como o Clock do pygame.
    """

    def __init__(self, fps: int):
        self.passo = 1.0 / max(1, fps)
        self.anterior = time.monotonic()

    def tick(self, fps: int | None = None) -> int:
        agora = time.monotonic()
        espera = self.passo - (agora - self.anterior)
        if espera > 0:
            time.sleep(espera)
        agora = time.monotonic()
        decorrido = agora - self.anterior
        self.anterior = agora
        return int(decorrido * 1000)


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

    # Um renderer de cada vez. No modo web nao existe janela do pygame:
    # quem desenha e o navegador, e o Python so publica o estado.
    #
    # O import do pygame mora AQUI dentro de proposito. No topo do arquivo
    # ele acontecia sempre — inclusive no modo web, que nao desenha nada.
    # O custo nao era so o banner no terminal: importar pygame abre o SDL,
    # entao `--web` exigia um ambiente grafico que ele nao usa. Servidor
    # remoto, sessao SSH ou maquina sem tela quebravam sem motivo.
    if args.web:
        ui = None
        servidor = ServidorWeb(porta=args.porta)
    else:
        import pygame

        from ui.pygame_ui import PygameUI

        ui = PygameUI(config, game)
        servidor = None

    adaptador = build_adapter(args, fila, config)

    if args.script:
        rodar_script(args.script, fila, config)

    if servidor is not None:
        servidor.iniciar()
        print(
            f"\n  Renderer 3D no ar. Abra no navegador:\n\n"
            f"      http://127.0.0.1:{servidor.porta}/\n\n"
            f"  Deixe a janela do navegador visivel: e ela que o OBS captura.\n"
            f"  Ctrl+C aqui encerra o jogo.\n"
        )

    adaptador.start()
    logger.info(
        "Sistema iniciado | modo=%s | renderer=%s | resolucao=%sx%s | escala=%s",
        "TESTE" if (args.test or args.script or args.burst) else "LIVE REAL",
        "web" if args.web else "pygame",
        config["app"]["window_width"],
        config["app"]["window_height"],
        config["app"]["render_scale"],
    )

    fps = config["app"].get("fps", 60)
    clock = Relogio(fps) if ui is None else pygame.time.Clock()
    por_frame = config["app"].get("events_per_frame", 25)
    rodando = True

    try:
        while rodando:
            dt = clock.tick(fps) / 1000.0
            agora = time.monotonic()

            acoes = ui.poll() if ui is not None else set()
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

            if ui is not None:
                ui.draw(adaptador.status, fila.size(), agora)
            else:
                # So guarda o retrato: quem fala com a rede e a thread do
                # servidor. Este caminho nunca bloqueia no soquete.
                servidor.publicar(snapshot(game.state, agora, adaptador.status, fila.size()))

    except KeyboardInterrupt:
        logger.info("Interrompido pelo teclado.")
    finally:
        adaptador.stop()
        # Drena o que sobrou para o journal nao perder os ultimos eventos.
        for evento in fila.drain(1000):
            journal.record(evento)
        journal.close()
        if servidor is not None:
            servidor.parar()
        if ui is not None:
            ui.close()
        logger.info(
            "Encerrado | aceitos=%s | descartados=%s",
            fila.accepted,
            fila.dropped,
        )

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
