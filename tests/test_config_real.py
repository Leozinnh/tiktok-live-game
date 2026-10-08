"""Valida o config.json que o projeto entrega.

`exigir_username=False` de proposito: o arquivo e entregue com o
placeholder `@SEU_USUARIO`, que o modo LIVE recusa e o modo teste aceita.
"""

from pathlib import Path

from core.config import load_config
from game.actions import known_actions

RAIZ = Path(__file__).resolve().parent.parent


def _cfg():
    return load_config(RAIZ / "config.json", exigir_username=False)


def test_config_do_projeto_e_valida():
    cfg = _cfg()
    assert cfg["app"]["window_width"] == 1080
    assert cfg["app"]["window_height"] == 1920


def test_pelo_menos_dez_presentes():
    cfg = _cfg()
    assert len(cfg["rules"]["gifts"]) >= 10


def test_todos_os_tipos_de_acao_do_pedido_estao_configurados():
    cfg = _cfg()
    configuradas = {r["action"] for r in cfg["rules"]["gifts"]}
    exigidas = {
        "xp", "run", "jump", "heal", "speed", "shield",
        "damage", "spawn_enemy", "special", "boss", "mega",
    }
    assert exigidas <= configuradas


def test_toda_acao_configurada_existe_no_registro():
    cfg = _cfg()
    for secao in ("gifts", "comments", "likes", "follows", "shares"):
        for regra in cfg["rules"].get(secao, []):
            assert regra["action"] in known_actions(), f"{secao}: {regra}"


def test_presentes_de_exemplo_do_pedido_estao_presentes():
    cfg = _cfg()
    nomes = {r.get("gift") for r in cfg["rules"]["gifts"]}
    assert {"Rose", "Heart Me", "GG"} <= nomes


def test_comandos_de_comentario_do_pedido_existem():
    cfg = _cfg()
    termos = {r["contains"] for r in cfg["rules"]["comments"]}
    assert {"corre", "pula", "xp", "direita", "esquerda"} <= termos


def test_likes_tem_milestone_de_100():
    cfg = _cfg()
    assert any(r["every"] == 100 for r in cfg["rules"]["likes"])


def test_follows_e_shares_dao_xp():
    cfg = _cfg()
    assert any(r["action"] == "xp" for r in cfg["rules"]["follows"])
    assert any(r["action"] == "xp" for r in cfg["rules"]["shares"])
