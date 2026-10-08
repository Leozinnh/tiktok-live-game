"""A janela 9:16 que o OBS captura.

Este e o unico modulo de UI que fala com o pygame de verdade. Ele nao
decide nada sobre o jogo: so le o GameState e desenha.
"""

import logging

import pygame

from adapters.base import AdapterStatus
from game.state import GameState
from ui.arena import Arena
from ui.feed import Feed
from ui.hud import Hud
from ui.overlay import Overlay
from ui.theme import TAMANHOS_FONTE, Theme
from ui.widgets import Draw, TextCache

logger = logging.getLogger(__name__)


class PygameUI:
    """Janela 9:16 pronta para o OBS capturar.

    Nao decide nada sobre o jogo: so le o GameState e desenha.
    """

    def __init__(self, config: dict, game):
        self.game = game
        self.theme = Theme.from_config(config)

        pygame.init()
        pygame.display.set_caption("TikTok LIVE Interactive Game")

        tamanho = self.theme.window_size()
        self.screen = pygame.display.set_mode(tamanho)
        self.texto = TextCache()

        escala_fonte = self.theme.scale
        self.fontes = {
            chave: pygame.font.SysFont(
                "Segoe UI", max(8, int(tamanho_px * escala_fonte)), bold=chave in {"titulo", "gigante"}
            )
            for chave, tamanho_px in TAMANHOS_FONTE.items()
        }

        self.draw_ctx = Draw(self.screen, self.theme, self.texto)
        self.hud = Hud(self.theme, self.fontes)
        self.feed = Feed(self.theme, self.fontes)
        self.overlay = Overlay(self.theme, self.fontes)
        self.arena = Arena(self.theme, self.fontes)
        self.background = self.theme.cores["fundo"]

    def poll(self) -> set[str]:
        """Le a fila do pygame. Retorna o conjunto de acoes de teclado."""
        acoes: set[str] = set()
        for evento in pygame.event.get():
            if evento.type == pygame.QUIT:
                acoes.add("quit")
            elif evento.type == pygame.KEYDOWN:
                if evento.key == pygame.K_ESCAPE:
                    acoes.add("quit")
                elif evento.key == pygame.K_F5:
                    acoes.add("teste_comentario")
                elif evento.key == pygame.K_F6:
                    acoes.add("teste_presente")
                elif evento.key == pygame.K_F7:
                    acoes.add("teste_rajada")
        return acoes

    def draw(self, status: AdapterStatus, fila: int, agora: float) -> None:
        state: GameState = self.game.state

        # A arena precisa da intencao para desenhar a faixa de direcao.
        state.intent_display = self.game.intent()

        self.screen.fill(self.background)
        self.hud.draw(
            self.draw_ctx,
            state,
            status,
            fila,
            self.game.xp_para_subir(state.level),
        )
        self.arena.draw(self.draw_ctx, state)
        self.feed.draw(self.draw_ctx, state)
        self.overlay.draw(self.draw_ctx, state, agora)

        pygame.display.flip()

    def close(self) -> None:
        try:
            self.texto.limpar()
        finally:
            pygame.quit()
