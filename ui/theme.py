"""Tema e layout vertical 9:16.

Sem import de pygame de proposito: medidas e retangulos sao testaveis sem
video, e o layout pode ser conferido antes de existir uma janela.
"""

from dataclasses import dataclass, field

# Resolucao logica de projeto. Todo o layout e escrito nestas unidades.
LARGURA_LOGICA = 1080
ALTURA_LOGICA = 1920

# Faixas verticais. O TikTok sobrepoe legenda e botoes no topo e na base,
# por isso o HUD e o feed nao encostam nas bordas.
TOPO_HUD = 40
# Respiro entre a ultima linha do HUD e a arena, para o rodape nao encostar
# na linha divisoria.
RESPIRO_HUD = 16
ALTURA_HUD = 320
ALTURA_FEED = 430
MARGEM = 28

# Tamanho nominal de cada fonte, em unidades logicas. O layout e a criacao
# das fontes leem daqui: duas tabelas divergindo e como o HUD quebra.
TAMANHOS_FONTE = {
    "minima": 20,
    "pequena": 26,
    "media": 34,
    "titulo": 46,
    "gigante": 92,
}

# Uma linha ocupa mais que o tamanho nominal da fonte: no Segoe UI a altura
# real e ~1.35x o nominal. Posicionar as linhas pelo valor nominal fazia o
# HUD transbordar para dentro da arena.
ENTRELINHA = 1.35


def altura_da_linha(chave: str) -> float:
    """Altura esperada de uma linha, em unidades logicas."""
    return TAMANHOS_FONTE[chave] * ENTRELINHA


def altura_do_texto(fontes: dict, chave: str, escala: float = 1.0) -> float:
    """Altura real de uma linha, em unidades logicas.

    A fonte do sistema pode ser mais alta que o tamanho nominal e ela e
    criada em pixels (ja escalada); quando informa a propria altura, essa
    medida manda. Sem fonte, cai no valor calculado de `altura_da_linha`.
    """
    medir = getattr(fontes.get(chave), "get_height", None)
    if callable(medir):
        return float(medir()) / escala
    return altura_da_linha(chave)

CORES = {
    "fundo": (14, 16, 24),
    "painel": (26, 30, 42),
    "painel_claro": (38, 44, 60),
    "texto": (238, 241, 248),
    "texto_fraco": (152, 160, 178),
    "hp": (232, 72, 78),
    "xp": (74, 152, 255),
    "verde": (62, 208, 118),
    "amarelo": (246, 200, 62),
    "roxo": (176, 96, 246),
    "laranja": (250, 146, 54),
    "ciano": (62, 214, 220),
    "inimigo": (232, 82, 88),
    "boss": (168, 52, 200),
    "personagem": (250, 214, 88),
    "chao": (58, 64, 82),
}


@dataclass(frozen=True)
class Rect:
    """Retangulo simples, em unidades logicas. Sem dependencia de pygame."""

    x: float
    y: float
    w: float
    h: float

    @property
    def left(self) -> float:
        return self.x

    @property
    def right(self) -> float:
        return self.x + self.w

    @property
    def top(self) -> float:
        return self.y

    @property
    def bottom(self) -> float:
        return self.y + self.h

    def to_px(self, escala: float) -> tuple[int, int, int, int]:
        return (
            int(self.x * escala),
            int(self.y * escala),
            int(self.w * escala),
            int(self.h * escala),
        )


@dataclass
class Theme:
    width: int = LARGURA_LOGICA
    height: int = ALTURA_LOGICA
    scale: float = 1.0
    feed_size: int = 6
    hud_height: float = ALTURA_HUD
    feed_height: float = ALTURA_FEED
    cores: dict = field(default_factory=lambda: dict(CORES))
    rects: dict = field(default_factory=dict)

    @classmethod
    def from_config(cls, config: dict) -> "Theme":
        app = config.get("app", {})
        escala = float(app.get("render_scale", 1.0))
        if escala <= 0:
            raise ValueError(f"render_scale precisa ser maior que zero (veio {escala}).")

        tema = cls(
            width=LARGURA_LOGICA,
            height=ALTURA_LOGICA,
            scale=escala,
            feed_size=int(app.get("feed_size", 6)),
            hud_height=float(app.get("hud_height", ALTURA_HUD)),
            feed_height=float(app.get("feed_height", ALTURA_FEED)),
        )
        tema.rects = tema._montar_layout()
        return tema

    def _montar_layout(self) -> dict[str, Rect]:
        largura_util = self.width - MARGEM * 2
        topo_arena = self.hud_height
        base_arena = self.height - self.feed_height

        return {
            "hud": Rect(MARGEM, TOPO_HUD, largura_util, topo_arena - TOPO_HUD),
            "arena": Rect(0, topo_arena, self.width, base_arena - topo_arena),
            "feed": Rect(MARGEM, base_arena, largura_util, self.feed_height - MARGEM),
        }

    def window_size(self) -> tuple[int, int]:
        return (
            max(1, int(self.width * self.scale)),
            max(1, int(self.height * self.scale)),
        )
