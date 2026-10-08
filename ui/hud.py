"""Topo da tela: barra de HP, barra de XP, nivel e contadores da LIVE."""

from game.state import GameState
from ui.theme import RESPIRO_HUD, Rect, Theme, altura_do_texto
from ui.widgets import Draw


class Hud:
    """Topo da tela: HP, XP, nivel e contadores da LIVE."""

    # Linhas do HUD, de cima para baixo, e a fonte que cada uma usa.
    LINHAS = ("titulo", "hp", "xp", "rodape")

    def __init__(self, theme: Theme, fontes: dict):
        self.theme = theme
        self.fontes = fontes

    def _altura(self, chave: str) -> float:
        """Altura real de uma linha do HUD, em unidades logicas."""
        return altura_do_texto(self.fontes, chave, self.theme.scale)

    def layout(self, r: Rect) -> dict[str, Rect]:
        """Caixa de cada linha do HUD, sempre dentro de `r`.

        As alturas vem da fonte real. Se a soma nao couber na faixa — uma
        fonte de sistema mais alta que o esperado — as linhas encolhem na
        mesma proporcao, em vez de empurrar o HUD para dentro da arena.
        """
        altura_util = max(0.0, r.h - RESPIRO_HUD)
        base = r.y + altura_util
        alturas = {
            "titulo": self._altura("titulo"),
            "hp": self._altura("media"),
            "xp": self._altura("media"),
            "rodape": self._altura("media") + self._altura("minima"),
        }
        total = sum(alturas.values())
        folga = altura_util - total
        if folga < 0:
            fator = altura_util / total if total > 0 else 0.0
            alturas = {nome: altura * fator for nome, altura in alturas.items()}
            folga = 0.0
        vao = folga / (len(alturas) - 1)

        caixas: dict[str, Rect] = {}
        y = r.y
        for i, nome in enumerate(self.LINHAS):
            # A ultima linha absorve o arredondamento: o conteudo termina
            # exatamente no fim da area util.
            altura = base - y if i == len(self.LINHAS) - 1 else alturas[nome]
            caixas[nome] = Rect(r.x, y, r.w, altura)
            y += altura + vao
        return caixas

    def _topo_do_texto(self, caixa: Rect, chave: str) -> float:
        """`y` para o texto ficar centrado na vertical da caixa.

        `Draw.texto_em` recebe o TOPO do texto, nao a linha de base, e a
        superficie tem a altura real da fonte — por isso o calculo usa
        `_altura` e nao o tamanho nominal.
        """
        return caixa.y + max(0.0, (caixa.h - self._altura(chave)) / 2)

    def draw(self, d: Draw, state: GameState, status, fila: int, xp_necessario: int) -> None:
        r = self.theme.rects["hud"]
        c = self.theme.cores
        caixas = self.layout(r)

        titulo = caixas["titulo"]
        d.texto_em("TIKTOK GAME", titulo.x, self._topo_do_texto(titulo, "titulo"), self.fontes["titulo"])

        ao_vivo = "AO VIVO" if status.connected else status.detail.upper()
        if fila > 0:
            ao_vivo = f"{ao_vivo}  -  fila {fila}"
        cor = c["hp"] if status.connected else c["texto_fraco"]
        meio_do_titulo = titulo.y + titulo.h / 2
        d.circulo(titulo.right - 230, meio_do_titulo, 12, cor)
        d.texto_em(ao_vivo, titulo.right - 205, self._topo_do_texto(titulo, "pequena"),
                   self.fontes["pequena"], cor)

        for nome, rotulo, valor, maximo, cor, texto in (
            ("hp", "HP", state.hp, state.max_hp, c["hp"], f"{state.hp}/{state.max_hp}"),
            ("xp", "XP", state.xp, max(1, xp_necessario), c["xp"],
             f"{state.xp}/{xp_necessario}"),
        ):
            caixa = caixas[nome]
            meio = caixa.y + caixa.h / 2
            altura_barra = max(6.0, caixa.h * 0.5)
            d.texto_em(rotulo, caixa.x, self._topo_do_texto(caixa, "media"),
                       self.fontes["media"], cor)
            d.barra(Rect(caixa.x + 70, meio - altura_barra / 2, caixa.w - 350, altura_barra),
                    valor, maximo, cor)
            d.texto_em(texto, caixa.right - 260, self._topo_do_texto(caixa, "pequena"),
                       self.fontes["pequena"], c["texto_fraco"])

        # Rodape: nivel e contadores da LIVE, lado a lado.
        rodape = caixas["rodape"]
        itens = [
            (f"NIVEL {state.level}", "Nivel", c["amarelo"]),
            (str(state.total_gifts), "Presentes", c["laranja"]),
            (str(state.total_likes), "Likes", c["hp"]),
            (str(state.total_followers), "Follows", c["verde"]),
            (str(state.total_shares), "Shares", c["ciano"]),
        ]
        coluna = rodape.w / len(itens)
        altura_valor, altura_rotulo = self._altura("media"), self._altura("minima")
        # Com a linha encolhida o rotulo desce proporcionalmente, em vez de
        # escapar da caixa.
        passo = altura_valor * min(1.0, rodape.h / max(1.0, altura_valor + altura_rotulo))
        for i, (valor, rotulo, cor) in enumerate(itens):
            x = rodape.x + coluna * i
            d.texto_em(valor, x, rodape.y, self.fontes["media"], cor)
            d.texto_em(rotulo, x, rodape.y + passo, self.fontes["minima"], c["texto_fraco"])
