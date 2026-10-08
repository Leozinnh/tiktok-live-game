"""Testes da janela. Sem display de verdade: SDL_VIDEODRIVER=dummy.

Precisa ser definido ANTES de qualquer `pygame.display.init()`, por isso o
setdefault vem no topo do modulo, antes do import de pygame.
"""

import os

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")

import pygame  # noqa: E402

from adapters.base import AdapterStatus  # noqa: E402
from game.engine import GameEngine  # noqa: E402
from ui.pygame_ui import PygameUI  # noqa: E402

CFG = {
    "app": {"window_width": 1080, "window_height": 1920, "render_scale": 0.4, "feed_size": 6},
    "game": {"max_hp": 100, "initial_hp": 100, "initial_speed": 220},
    "limits": {"max_enemies": 10},
}


def _ui():
    return PygameUI(CFG, GameEngine(CFG))


def test_a_janela_abre_no_tamanho_vertical_9_16():
    ui = _ui()
    try:
        assert ui.screen.get_size() == (432, 768)
    finally:
        ui.close()


def test_desenhar_um_frame_nao_quebra():
    ui = _ui()
    try:
        ui.draw(AdapterStatus(connected=True, detail="ao vivo"), 0, 0.0)
    finally:
        ui.close()


def test_poll_sem_eventos_devolve_conjunto_vazio():
    ui = _ui()
    try:
        pygame.event.clear()
        assert ui.poll() == set()
    finally:
        ui.close()


def test_escape_e_fechar_a_janela_pedem_quit():
    ui = _ui()
    try:
        pygame.event.clear()
        pygame.event.post(pygame.event.Event(pygame.KEYDOWN, key=pygame.K_ESCAPE))
        assert "quit" in ui.poll()

        pygame.event.post(pygame.event.Event(pygame.QUIT))
        assert "quit" in ui.poll()
    finally:
        ui.close()


def test_as_teclas_de_teste_viram_acoes():
    ui = _ui()
    try:
        for tecla, acao in (
            (pygame.K_F5, "teste_comentario"),
            (pygame.K_F6, "teste_presente"),
            (pygame.K_F7, "teste_rajada"),
        ):
            pygame.event.clear()
            pygame.event.post(pygame.event.Event(pygame.KEYDOWN, key=tecla))
            assert ui.poll() == {acao}
    finally:
        ui.close()


def test_draw_publica_a_intencao_do_motor_no_estado():
    ui = _ui()
    try:
        ui.game.steer(1)
        for _ in range(30):
            ui.game.update(1 / 60)
        ui.draw(AdapterStatus(), 0, 0.0)
        assert ui.game.state.intent_display == ui.game.intent()
        assert ui.game.state.intent_display > 0
    finally:
        ui.close()
