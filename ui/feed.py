"""Rodape: os eventos mais recentes da LIVE, um por linha."""

from game.effects import Announcement
from game.state import GameState
from ui.theme import Theme, altura_do_texto
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

    # Distancia do topo da faixa ate a primeira linha de evento.
    TOPO_DAS_LINHAS = 74
    # Espaco entre o fim de uma linha e o comeco da seguinte.
    VAO_ENTRE_LINHAS = 8

    def __init__(self, theme: Theme, fontes: dict):
        self.theme = theme
        self.fontes = fontes

    def linhas_visiveis(self, r) -> int:
        """Quantas linhas de evento cabem na faixa, no maximo `feed_size`.

        O texto nao encolhe com o config, entao um `feed_size` grande demais
        mostra menos linhas — nunca linhas fora da faixa.
        """
        passo = altura_do_texto(self.fontes, "pequena", self.theme.scale)
        passo += self.VAO_ENTRE_LINHAS
        cabem = int((r.h - self.TOPO_DAS_LINHAS) // passo)
        return max(1, min(self.theme.feed_size, cabem))

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

        y = r.y + self.TOPO_DAS_LINHAS
        altura_linha = altura_do_texto(self.fontes, "pequena", self.theme.scale)
        altura_linha += self.VAO_ENTRE_LINHAS
        for ann in anuncios[-self.linhas_visiveis(r) :]:
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
