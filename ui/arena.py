"""O mundo do jogo: chao, personagem, inimigos e chefe."""

from game.state import GameState
from ui.theme import Rect, Theme
from ui.widgets import Draw


class Arena:
    """O mundo do jogo: chao, personagem, inimigos e chefe."""

    def __init__(self, theme: Theme, fontes: dict):
        self.theme = theme
        self.fontes = fontes

    def draw(self, d: Draw, state: GameState) -> None:
        r = self.theme.rects["arena"]
        c = self.theme.cores

        d.panel(r, c["fundo"], raio=0)

        # Chao
        chao_y = state.character.y + state.character.radius + 18
        d.rect(Rect(r.x, chao_y, r.w, 6), c["chao"], raio=3)

        # Faixa de direcao: mostra para onde o publico esta empurrando.
        self._faixa_de_intencao(d, r, state)

        for inimigo in state.enemies:
            self._inimigo(d, inimigo)
        if state.boss is not None and state.boss.is_alive():
            self._boss(d, r, state)
        self._personagem(d, state)

    def _faixa_de_intencao(self, d: Draw, r: Rect, state: GameState) -> None:
        intencao = getattr(state, "intent_display", 0.0)
        if abs(intencao) < 0.05:
            return
        largura = min(abs(intencao), 1.0) * (r.w / 2 - 40)
        x = r.x + r.w / 2 if intencao > 0 else r.x + r.w / 2 - largura
        d.rect(Rect(x, r.y + 16, largura, 10), self.theme.cores["ciano"], raio=5)

    def _personagem(self, d: Draw, state: GameState) -> None:
        p = state.character
        y = p.y - p.y_offset
        cor = self.theme.cores["personagem"]

        if state.effects.active("mega"):
            cor = self.theme.cores["roxo"]
        elif state.effects.active("rage"):
            cor = self.theme.cores["hp"]

        # Sombra no chao, que encolhe durante o pulo.
        encolhimento = 1.0 - min(0.5, p.y_offset / 300)
        d.circulo(p.x, p.y + p.radius + 14, p.radius * encolhimento, self.theme.cores["chao"])

        d.circulo(p.x, y - p.radius, p.radius, cor)
        d.rect(Rect(p.x - p.radius * 0.8, y - p.radius * 0.3,
                    p.radius * 1.6, p.radius * 1.6), cor, raio=12)

        if state.effects.active("shield"):
            d.circulo(p.x, y - p.radius, p.radius * 1.9, self.theme.cores["ciano"])

        if state.effects.active("run"):
            for i in range(3):
                d.rect(
                    Rect(p.x - p.facing * (60 + i * 26), y - 10 - i * 6, 22, 6),
                    self.theme.cores["texto_fraco"],
                    raio=3,
                )

    def _inimigo(self, d: Draw, inimigo) -> None:
        d.circulo(inimigo.x, inimigo.y, inimigo.radius, self.theme.cores["inimigo"])
        d.rect(
            Rect(inimigo.x - inimigo.radius, inimigo.y + inimigo.radius + 6,
                 inimigo.radius * 2, 8),
            self.theme.cores["painel_claro"],
            raio=4,
        )

    def _boss(self, d: Draw, r: Rect, state: GameState) -> None:
        boss = state.boss
        c = self.theme.cores
        d.circulo(boss.x, boss.y, boss.radius, c["boss"])

        barra = Rect(r.x + 60, r.y + 36, r.w - 120, 26)
        d.barra(barra, boss.hp_fraction(), 1.0, c["hp"])
        d.texto_em("CHEFAO", 0, r.y + 74, self.fontes["media"], c["texto"],
                   centralizado_em=r.x + r.w / 2)
