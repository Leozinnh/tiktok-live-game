import pytest

from ui.theme import Theme


def _cfg(escala=1.0, w=1080, h=1920):
    return {"app": {"window_width": w, "window_height": h, "render_scale": escala, "feed_size": 6}}


def test_resolucao_logica_e_sempre_1080x1920():
    t = Theme.from_config(_cfg(escala=0.5))
    assert t.width == 1080
    assert t.height == 1920


def test_escala_muda_o_tamanho_da_janela():
    assert Theme.from_config(_cfg(escala=0.5)).window_size() == (540, 960)
    assert Theme.from_config(_cfg(escala=1.0)).window_size() == (1080, 1920)


def test_window_size_nunca_e_menor_que_1():
    t = Theme.from_config(_cfg(escala=0.0001))
    w, h = t.window_size()
    assert w >= 1 and h >= 1


def test_escala_zero_e_recusada():
    with pytest.raises(ValueError):
        Theme.from_config(_cfg(escala=0.0))


def test_as_faixas_do_layout_nao_se_sobrepoem():
    t = Theme.from_config(_cfg())
    hud = t.rects["hud"]
    arena = t.rects["arena"]
    feed = t.rects["feed"]
    assert hud.bottom <= arena.top
    assert arena.bottom <= feed.top


def test_o_layout_cobre_a_altura_toda():
    t = Theme.from_config(_cfg())
    hud, arena, feed = t.rects["hud"], t.rects["arena"], t.rects["feed"]
    # As tres faixas sao contiguas: nao sobra buraco entre HUD, arena e feed.
    assert hud.bottom == arena.top
    assert arena.bottom == feed.top
    assert feed.bottom <= t.height


def test_o_hud_deixa_espaco_para_a_interface_do_tiktok():
    # O TikTok desenha nome, selo LIVE e contagem de espectadores no topo do
    # video. O HUD comeca abaixo disso para nao ficar escondido.
    assert Theme.from_config(_cfg()).rects["hud"].top > 0


def test_feed_size_vem_do_config():
    assert Theme.from_config(_cfg()).feed_size == 6
