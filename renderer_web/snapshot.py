"""Transforma o GameState no retrato que o navegador desenha.

Modulo puro: nao abre socket, nao conhece pygame nem Three.js. Recebe o
estado e devolve um dict pronto para `json.dumps` — o que torna o formato
do fio testavel sem subir servidor nenhum.

O retrato e um INSTANTANEO, nao um evento: o navegador recebe o estado
inteiro 20 vezes por segundo e so desenha. Nao ha replica de regra no
JavaScript, entao nao existe a possibilidade de o Python e o navegador
discordarem sobre o que aconteceu.

As coordenadas vao em unidades logicas do jogo (arena 1080x1920, Y para
baixo), exatamente como `GameState.to_dict()` ja entregava. Quem converte
para o mundo 3D e o renderer: assim o proximo renderer, se um dia houver
um Unity ou Godot, recebe os mesmos numeros sem tocar no motor.
"""

from game.state import GameState


def _efeitos(state: GameState) -> dict[str, float]:
    """Efeitos ativos com o tempo que ainda resta, em segundos."""
    conjunto = getattr(state, "effects", None)
    if conjunto is None:
        # `GameState()` cru (testes, ferramentas) nasce sem efeitos.
        return {}
    return {
        nome: round(conjunto.remaining(nome), 2) for nome in conjunto.active_names()
    }


def _anuncios(state: GameState, agora: float) -> list[dict]:
    """Avisos vivos, do mais antigo para o mais novo (o feed cresce para baixo)."""
    fila = getattr(state, "announcements", None)
    if fila is None:
        return []
    return [
        {
            "kind": a.kind,
            "actor": a.actor,
            "text": a.text,
            "detail": a.detail,
            "icon": a.icon,
            "big": a.big,
            "alpha": round(a.alpha(agora), 3),
        }
        for a in fila.active()
    ]


def snapshot(state: GameState, agora: float, status=None, fila: int = 0) -> dict:
    """Retrato completo: jogo + apresentacao + estado da conexao."""
    dados = state.to_dict()
    dados["intent"] = round(float(state.intent_display), 3)
    dados["effects"] = _efeitos(state)
    dados["announcements"] = _anuncios(state, agora)
    dados["status"] = {
        "conectado": bool(getattr(status, "connected", False)),
        "detalhe": str(getattr(status, "detail", "")),
        "fila": int(fila),
    }
    return dados
