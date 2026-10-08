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
ALTURA_HUD = 300
ALTURA_FEED = 430
MARGEM = 28

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
        )
        tema.rects = tema._montar_layout()
        return tema

    def _montar_layout(self) -> dict[str, Rect]:
        largura_util = self.width - MARGEM * 2
        feed_h = ALTURA_FEED
        arena_h = self.height - ALTURA_HUD - feed_h

        return {
            "hud": Rect(MARGEM, 40, largura_util, ALTURA_HUD - 40),
            "arena": Rect(0, ALTURA_HUD, self.width, arena_h),
            "feed": Rect(MARGEM, self.height - feed_h, largura_util, feed_h - MARGEM),
        }

    def window_size(self) -> tuple[int, int]:
        return (
            max(1, int(self.width * self.scale)),
            max(1, int(self.height * self.scale)),
        )
