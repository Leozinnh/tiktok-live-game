"""Rodape: os eventos mais recentes da LIVE, um por linha."""

from game.effects import Announcement
from game.state import GameState
from ui.theme import Theme
from ui.widgets import Draw

ICONES = {
    "gift": "PRESENTE",
    "comment": "COMENTARIO",
    "like": "LIKE",
    "follow": "FOLLOW",
    "share": "SHARE",
    "levelup": "NIVEL",
    "special": "ESPECIAL",
    "boss": "CHEFAO",
    "mega": "MEGA",
    "system": "SISTEMA",
}

# Sem emoji de proposito: a fonte padrao do pygame nao tem glifo de emoji e
# desenharia um quadrado vazio. Estes marcadores ASCII sempre aparecem.
ICONES_CURTOS = {
    "gift": "(*)",
    "comment": "(#)",
    "like": "(+)",
    "follow": "(+)",
    "share": "(>)",
    "levelup": "(^)",
    "special": "(!)",
    "boss": "(!)",
    "mega": "(!)",
    "system": "(-)",
}


def formatar_anuncio(ann: Announcement, largura_max: int = 46) -> tuple[str, str]:
    """Converte um anuncio em (icone, linha de texto). Funcao pura."""
    icone = ICONES_CURTOS.get(ann.kind, "(-)")

    partes = []
    if ann.actor:
        partes.append(ann.actor)
    if ann.text:
        partes.append(ann.text)
    if ann.detail:
        partes.append(ann.detail)

    linha = " ".join(partes).strip() or "evento"
    linha = " ".join(linha.split())  # colapsa espacos repetidos

    if len(linha) > largura_max:
        linha = linha[: largura_max - 1].rstrip() + "…"

    return icone, linha


class Feed:
    """Rodape: os eventos mais recentes da LIVE."""

    def __init__(self, theme: Theme, fontes: dict):
        self.theme = theme
        self.fontes = fontes

    def draw(self, d: Draw, state: GameState) -> None:
        r = self.theme.rects["feed"]
        c = self.theme.cores

        d.panel(r)
        d.texto_em("EVENTOS", r.x + 24, r.y + 18, self.fontes["media"], c["texto"])

        anuncios = list(state.announcements.active())
        if not anuncios:
            d.texto_em(
                "Aguardando a LIVE...",
                r.x + 24,
                r.y + 84,
                self.fontes["pequena"],
                c["texto_fraco"],
            )
            return

        y = r.y + 74
        altura_linha = 48
        for ann in anuncios[-self.theme.feed_size :]:
            icone, linha = formatar_anuncio(ann)
            cor = self._cor(ann, c)
            d.texto_em(icone, r.x + 24, y, self.fontes["pequena"], cor)
            d.texto_em(linha, r.x + 110, y, self.fontes["pequena"], c["texto"])
            y += altura_linha

    @staticmethod
    def _cor(ann: Announcement, c: dict):
        return {
            "gift": c["laranja"],
            "comment": c["xp"],
            "like": c["hp"],
            "follow": c["verde"],
            "share": c["ciano"],
            "levelup": c["amarelo"],
            "special": c["roxo"],
            "boss": c["roxo"],
            "mega": c["roxo"],
        }.get(ann.kind, c["texto_fraco"])
