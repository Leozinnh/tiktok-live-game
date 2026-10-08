"""Layout do HUD: nada pode ser desenhado fora da faixa do HUD.

O bug que estes testes travam: as linhas do HUD eram posicionadas pela
altura NOMINAL da fonte (46, 34, 20), mas a altura real de uma linha e
1.35x maior. O conteudo transbordava a faixa e caia dentro da arena.
"""

import pytest

from ui.hud import Hud
from ui.theme import RESPIRO_HUD, TAMANHOS_FONTE, Theme


class FonteFalsa:
    """Fonte de mentira: so sabe a propria altura de linha."""

    def __init__(self, altura: float):
        self._altura = altura

    def get_height(self) -> int:
        return int(self._altura)


def _fontes(fator: float = 1.35) -> dict:
    return {chave: FonteFalsa(px * fator) for chave, px in TAMANHOS_FONTE.items()}


def _hud(fator: float = 1.35, **app):
    tema = Theme.from_config({"app": app})
    return Hud(tema, _fontes(fator)), tema.rects["hud"]


def test_o_conteudo_do_hud_cabe_na_faixa():
    hud, r = _hud()
    caixas = hud.layout(r)
    assert caixas
    for nome, caixa in caixas.items():
        assert caixa.top >= r.top - 0.001, nome
        assert caixa.bottom <= r.bottom + 0.001, nome
        assert caixa.left >= r.left - 0.001, nome
        assert caixa.right <= r.right + 0.001, nome


def test_as_caixas_do_hud_nao_se_sobrepoem():
    hud, r = _hud()
    caixas = hud.layout(r)
    ordenadas = sorted(caixas.values(), key=lambda c: c.top)
    for anterior, seguinte in zip(ordenadas, ordenadas[1:]):
        assert anterior.bottom <= seguinte.top + 0.001


def test_o_hud_encolhe_as_folgas_quando_a_fonte_e_alta():
    # Uma fonte de sistema mais alta nao pode empurrar o HUD para a arena.
    hud, r = _hud(fator=1.8)
    for nome, caixa in hud.layout(r).items():
        assert caixa.bottom <= r.bottom + 0.001, nome


def test_a_caixa_do_titulo_usa_a_altura_real_da_fonte():
    # Nao o tamanho nominal: a caixa acompanha a altura que a fonte informa.
    hud, r = _hud()
    nominal = TAMANHOS_FONTE["titulo"]
    assert hud.layout(r)["titulo"].h > nominal
    assert hud.layout(r)["titulo"].h == pytest.approx(nominal * 1.35, abs=1.0)


def test_sem_fonte_o_hud_cai_na_altura_do_tema():
    tema = Theme.from_config({"app": {}})
    hud = Hud(tema, {})
    caixas = hud.layout(tema.rects["hud"])
    assert caixas["titulo"].h > TAMANHOS_FONTE["titulo"]


def test_o_hud_tem_as_linhas_de_hp_xp_e_contadores():
    hud, r = _hud()
    assert set(hud.layout(r)) == {"titulo", "hp", "xp", "rodape"}


def test_o_hud_deixa_respiro_antes_da_arena():
    hud, r = _hud()
    assert hud.layout(r)["rodape"].bottom <= r.bottom - RESPIRO_HUD + 0.001


def test_a_faixa_do_hud_vem_do_config():
    hud, r = _hud(hud_height=400)
    assert r.bottom == 400
    assert hud.layout(r)["rodape"].bottom <= 400
