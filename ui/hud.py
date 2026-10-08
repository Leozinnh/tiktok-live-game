"""Topo da tela: barra de HP, barra de XP, nivel e contadores da LIVE."""

from game.state import GameState
from ui.theme import Rect, Theme
from ui.widgets import Draw


class Hud:
    """Topo da tela: HP, XP, nivel e contadores da LIVE."""

    def __init__(self, theme: Theme, fontes: dict):
        self.theme = theme
        self.fontes = fontes

    def draw(self, d: Draw, state: GameState, status, fila: int, xp_necessario: int) -> None:
        r = self.theme.rects["hud"]
        c = self.theme.cores

        d.texto_em("TIKTOK GAME", r.x, r.y, self.fontes["titulo"])

        ao_vivo = "AO VIVO" if status.connected else status.detail.upper()
        cor = c["hp"] if status.connected else c["texto_fraco"]
        d.circulo(r.right - 210, r.y + 22, 12, cor)
        d.texto_em(ao_vivo, r.right - 190, r.y + 6, self.fontes["pequena"], cor)

        linhas = [
            ("HP", state.hp, state.max_hp, c["hp"], f"{state.hp}/{state.max_hp}"),
            ("XP", state.xp, max(1, xp_necessario), c["xp"], f"{state.xp}/{xp_necessario}"),
        ]
        y = r.y + 70
        for rotulo, valor, maximo, cor, texto in linhas:
            d.texto_em(rotulo, r.x, y, self.fontes["media"], cor)
            d.barra(Rect(r.x + 70, y + 6, r.w - 340, 26), valor, maximo, cor)
            d.texto_em(texto, r.right - 250, y, self.fontes["pequena"], c["texto_fraco"])
            y += 52

        d.texto_em(f"NIVEL {state.level}", r.x, y, self.fontes["titulo"], c["amarelo"])

        # Contadores da LIVE, lado a lado.
        y += 62
        itens = [
            ("Presentes", state.total_gifts, c["laranja"]),
            ("Likes", state.total_likes, c["hp"]),
            ("Follows", state.total_followers, c["verde"]),
            ("Shares", state.total_shares, c["ciano"]),
        ]
        coluna = r.w / len(itens)
        for i, (rotulo, valor, cor) in enumerate(itens):
            x = r.x + coluna * i
            d.texto_em(str(valor), x, y, self.fontes["media"], cor)
            d.texto_em(rotulo, x, y + 34, self.fontes["minima"], c["texto_fraco"])

        if fila > 0:
            d.texto_em(f"fila: {fila}", r.x, y + 76, self.fontes["minima"], c["texto_fraco"])
