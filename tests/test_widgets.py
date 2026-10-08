import pygame

from ui.theme import Rect, Theme
from ui.widgets import Draw, TextCache

BRANCO = (255, 255, 255)
VERMELHO = (255, 0, 0)


class FonteFalsa:
    """Fonte de mentira: conta renderizacoes em vez de rasterizar.

    `pygame.font.Font` de verdade exigiria `pygame.font.init()` e um arquivo
    de fonte. Para testar CACHE, o que importa e quantas vezes render() roda.
    """

    def __init__(self):
        self.chamadas = 0

    def render(self, texto, antialiased, cor):
        self.chamadas += 1
        return pygame.Surface((max(1, len(texto) * 10), 20))


def _tema():
    return Theme.from_config({"app": {"render_scale": 1.0, "feed_size": 6}})


def test_textcache_nao_renderiza_duas_vezes():
    cache, fonte = TextCache(), FonteFalsa()
    a = cache.render(fonte, "oi", BRANCO)
    b = cache.render(fonte, "oi", BRANCO)
    assert a is b
    assert fonte.chamadas == 1


def test_textcache_separa_por_texto_e_por_cor():
    cache, fonte = TextCache(), FonteFalsa()
    cache.render(fonte, "oi", BRANCO)
    cache.render(fonte, "oi", VERMELHO)
    cache.render(fonte, "ola", BRANCO)
    assert fonte.chamadas == 3


def test_textcache_respeita_o_limite_e_descarta_o_antigo():
    cache, fonte = TextCache(limite=4), FonteFalsa()
    cache.render(fonte, "primeira", BRANCO)
    for i in range(20):
        cache.render(fonte, f"linha {i}", BRANCO)
    # A chave antiga foi descartada, entao renderiza de novo.
    cache.render(fonte, "primeira", BRANCO)
    assert fonte.chamadas == 22


def test_limpar_esvazia_o_cache():
    cache, fonte = TextCache(), FonteFalsa()
    cache.render(fonte, "oi", BRANCO)
    cache.limpar()
    cache.render(fonte, "oi", BRANCO)
    assert fonte.chamadas == 2


def test_barra_preenche_so_a_fatia_correspondente():
    tema = _tema()
    superficie = pygame.Surface(tema.window_size())
    d = Draw(superficie, tema, TextCache())
    d.barra(Rect(100, 100, 200, 20), 50, 100, VERMELHO)

    assert superficie.get_at((150, 110))[:3] == VERMELHO  # metade esquerda
    assert superficie.get_at((250, 110))[:3] != VERMELHO  # metade direita


def test_barra_com_maximo_zero_nao_pinta():
    tema = _tema()
    superficie = pygame.Surface(tema.window_size())
    d = Draw(superficie, tema, TextCache())
    d.barra(Rect(100, 100, 200, 20), 10, 0, VERMELHO)
    assert superficie.get_at((150, 110))[:3] != VERMELHO
