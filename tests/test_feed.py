"""O feed cabe na faixa, seja qual for o `feed_size` configurado.

Mesmo bug do HUD, no rodape: as linhas eram posicionadas por uma altura
fixa (48), entao subir `feed_size` no config fazia o feed transbordar.
"""

import pytest

from game.effects import AnnouncementQueue
from game.state import GameState
from ui.feed import Feed
from ui.theme import TAMANHOS_FONTE, Theme


class FonteFalsa:
    """Fonte de mentira: so sabe a propria altura de linha (em pixels)."""

    def __init__(self, altura: float):
        self._altura = altura

    def get_height(self) -> float:
        return self._altura


class DrawEspiao:
    """Anota o que seria desenhado, sem abrir janela."""

    def __init__(self):
        self.textos: list[tuple[str, float, float, object]] = []

    def panel(self, r, cor=None, raio=24) -> None:
        pass

    def texto_em(self, texto, x, y, fonte, cor=None, centralizado_em=None) -> None:
        self.textos.append((texto, x, y, fonte))


def _fontes(fator: float = 1.35) -> dict:
    return {chave: FonteFalsa(px * fator) for chave, px in TAMANHOS_FONTE.items()}


def _estado(quantidade: int) -> GameState:
    fila = AnnouncementQueue()
    for i in range(quantidade):
        fila.push(kind="gift", actor=f"user_{i}", text="mandou um presente", ttl=60.0)
    return GameState(announcements=fila)


@pytest.mark.parametrize("tamanho", [1, 6, 8, 12, 20])
def test_o_feed_cabe_na_faixa(tamanho):
    tema = Theme.from_config({"app": {"feed_size": tamanho}})
    r = tema.rects["feed"]
    d = DrawEspiao()
    Feed(tema, _fontes()).draw(d, _estado(tamanho))
    assert d.textos
    for texto, _x, y, fonte in d.textos:
        assert y >= r.top, (tamanho, texto)
        assert y + fonte.get_height() <= r.bottom, (tamanho, texto)


def test_o_feed_mostra_no_maximo_feed_size_linhas():
    tema = Theme.from_config({"app": {"feed_size": 4}})
    d = DrawEspiao()
    Feed(tema, _fontes()).draw(d, _estado(10))
    linhas = {y for _texto, _x, y, _fonte in d.textos}
    # 1 cabecalho + no maximo 4 linhas de evento (cada evento desenha
    # icone e texto na mesma altura, por isso contamos as alturas).
    assert len(linhas) - 1 == 4


def test_o_feed_avisa_quando_nao_ha_evento():
    tema = Theme.from_config({"app": {}})
    d = DrawEspiao()
    Feed(tema, _fontes()).draw(d, _estado(0))
    assert any("Aguardando" in texto for texto, _x, _y, _f in d.textos)
