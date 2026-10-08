import logging
import queue
import threading
import time
from pathlib import Path

import pygame

from core.config import load_config
from core.events import LiveEvent
from core.event_queue import EventQueue
from core.rules import RuleEngine
from game.engine import GameEngine
from adapters.tiktok_live import TikTokLiveAdapter
from ui.pygame_ui import PygameUI


def configure_logging():
    Path("logs").mkdir(exist_ok=True)
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
        handlers=[
            logging.FileHandler("logs/app.log", encoding="utf-8"),
            logging.StreamHandler(),
        ],
    )


def main():
    configure_logging()
    logger = logging.getLogger("main")

    config = load_config("config.json")
    event_queue = EventQueue(maxsize=config["app"].get("queue_max_size", 5000))

    game = GameEngine(config)
    rules = RuleEngine(config, game)
    ui = PygameUI(config, game)

    def on_live_event(event: LiveEvent):
        event_queue.put(event)

    adapter = TikTokLiveAdapter(
        username=config["tiktok"]["username"],
        event_sink=on_live_event,
        reconnect_seconds=config["tiktok"].get("reconnect_seconds", 5),
        fetch_gift_info=config["tiktok"].get("fetch_gift_info", True),
    )

    adapter.start()

    logger.info("Sistema iniciado. Pressione ESC ou feche a janela para sair.")

    running = True
    clock = pygame.time.Clock()

    try:
        while running:
            dt = clock.tick(config["app"].get("fps", 60)) / 1000.0

            for pg_event in pygame.event.get():
                if pg_event.type == pygame.QUIT:
                    running = False
                elif pg_event.type == pygame.KEYDOWN and pg_event.key == pygame.K_ESCAPE:
                    running = False
                elif pg_event.type == pygame.KEYDOWN and pg_event.key == pygame.K_F5:
                    # F5: evento de teste local.
                    event_queue.put(
                        LiveEvent(
                            type="comment",
                            username="teste_local",
                            display_name="Teste Local",
                            text="corre",
                        )
                    )

            # Limita o trabalho por frame para evitar que uma rajada de eventos
            # congele a interface.
            for _ in range(config["app"].get("events_per_frame", 20)):
                event = event_queue.get_nowait()
                if event is None:
                    break
                try:
                    rules.process(event)
                except Exception:
                    logger.exception("Erro processando evento: %s", event)

            game.update(dt)
            ui.draw(event_queue.size())

    except KeyboardInterrupt:
        logger.info("Interrupção pelo teclado.")
    finally:
        adapter.stop()
        ui.close()
        logger.info("Sistema encerrado.")


if __name__ == "__main__":
    main()
