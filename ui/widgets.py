"""Primitivas de desenho.

Tudo recebe e devolve unidades LOGICAS (1080x1920). A escala para o
tamanho real da janela acontece aqui dentro, num lugar so.
"""

import pygame

from ui.theme import Rect, Theme


class TextCache:
    """Cache de superficies de texto.

    `font.render()` e a operacao mais cara do frame em 1080x1920. Sem este
    cache, 60 FPS nao se sustentam.
    """

    def __init__(self, limite: int = 512):
        self._cache: dict[tuple, pygame.Surface] = {}
        self._limite = limite

    def render(self, font: pygame.font.Font, texto: str, cor: tuple) -> pygame.Surface:
        chave = (id(font), texto, cor)
        achado = self._cache.get(chave)
        if achado is not None:
            return achado

        if len(self._cache) >= self._limite:
            self._cache.clear()

        superficie = font.render(texto, True, cor)
        self._cache[chave] = superficie
        return superficie

    def limpar(self) -> None:
        self._cache.clear()


class Draw:
    """Primitivas de desenho, todas em unidades logicas."""

    def __init__(self, surface: pygame.Surface, theme: Theme, texto: TextCache):
        self.surface = surface
        self.theme = theme
        self.texto = texto
        self.s = theme.scale

    def _px(self, valor: float) -> int:
        return int(valor * self.s)

    def rect(self, r: Rect, cor, raio: float = 0) -> None:
        pygame.draw.rect(self.surface, cor, r.to_px(self.s), border_radius=self._px(raio))

    def panel(self, r: Rect, cor=None, raio: float = 24) -> None:
        self.rect(r, cor or self.theme.cores["painel"], raio)

    def barra(self, r: Rect, valor: float, maximo: float, cor) -> None:
        self.rect(r, self.theme.cores["painel_claro"], r.h / 2)
        if maximo <= 0:
            return
        razao = max(0.0, min(1.0, valor / maximo))
        if razao <= 0:
            return

        self.rect(Rect(r.x, r.y, r.w * razao, r.h), cor, r.h / 2)

    def texto_em(
        self,
        texto: str,
        x: float,
        y: float,
        fonte: pygame.font.Font,
        cor=None,
        centralizado_em: float | None = None,
    ) -> None:
        superficie = self.texto.render(fonte, texto, cor or self.theme.cores["texto"])
        if centralizado_em is not None:
            x = centralizado_em - superficie.get_width() / (2 * self.s)
        self.surface.blit(superficie, (self._px(x), self._px(y)))

    def circulo(self, x: float, y: float, raio: float, cor) -> None:
        pygame.draw.circle(self.surface, cor, (self._px(x), self._px(y)), self._px(raio))
