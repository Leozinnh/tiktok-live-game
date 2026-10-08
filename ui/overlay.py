"""Banners de tela cheia, sobre a arena."""

from game.state import GameState
from ui.theme import Rect, Theme
from ui.widgets import Draw


class Overlay:
    """Banners de tela cheia: LEVEL UP, MEGA EVENTO, EVENTO ESPECIAL."""

    def __init__(self, theme: Theme, fontes: dict):
        self.theme = theme
        self.fontes = fontes

    def draw(self, d: Draw, state: GameState, agora: float) -> None:
        grandes = [a for a in state.announcements.active() if a.big]
        if not grandes:
            return

        # Mostra apenas o mais recente: varios banners empilhados viram sopa.
        ann = grandes[-1]
        alpha = ann.alpha(agora)
        if alpha <= 0:
            return

        arena = self.theme.rects["arena"]
        altura = 220
        r = Rect(arena.x + 40, arena.y + arena.h / 2 - altura / 2, arena.w - 80, altura)

        fundo = self._escurecer(self._cor(ann.kind), 0.25)
        superficie = _superficie_com_alpha(self.theme, r, fundo, alpha)
        if superficie is None:
            # Alpha cheio: caminho rapido, sem alocar superficie extra.
            d.panel(r, fundo)
        else:
            d.surface.blit(superficie, r.to_px(self.theme.scale)[:2])

        centro = r.x + r.w / 2
        d.texto_em(ann.text, 0, r.y + 40, self.fontes["gigante"], self.theme.cores["texto"],
                   centralizado_em=centro)
        if ann.detail:
            d.texto_em(ann.detail, 0, r.y + 140, self.fontes["media"],
                       self.theme.cores["texto"], centralizado_em=centro)

    def _cor(self, kind: str):
        c = self.theme.cores
        return {
            "levelup": c["amarelo"],
            "special": c["roxo"],
            "boss": c["roxo"],
            "mega": c["roxo"],
            "system": c["hp"],
        }.get(kind, c["xp"])

    @staticmethod
    def _escurecer(cor, fator: float):
        return tuple(max(0, min(255, int(v * fator))) for v in cor)


def _superficie_com_alpha(theme: Theme, r: Rect, cor, alpha: float):
    import pygame

    if alpha >= 0.99:
        return None
    largura, altura = int(r.w * theme.scale), int(r.h * theme.scale)
    if largura <= 0 or altura <= 0:
        return None
    superficie = pygame.Surface((largura, altura), pygame.SRCALPHA)
    superficie.fill((*cor, int(255 * alpha)))
    return superficie
