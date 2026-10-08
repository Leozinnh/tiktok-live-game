import json

import pytest

from core.config import ConfigError, load_config, validate_config


def _base() -> dict:
    return {
        "app": {"fps": 60, "window_width": 1080, "window_height": 1920, "render_scale": 1.0},
        "tiktok": {"username": "@alguem"},
        "game": {"max_hp": 100},
        "rules": {"gifts": [], "comments": [], "likes": [], "follows": [], "shares": []},
    }


def test_config_valida_passa():
    validate_config(_base())


def test_acao_desconhecida_e_recusada_com_nome_do_presente():
    cfg = _base()
    cfg["rules"]["gifts"] = [{"gift": "Rose", "action": "corree"}]
    with pytest.raises(ConfigError) as exc:
        validate_config(cfg)
    assert "Rose" in str(exc.value)
    assert "corree" in str(exc.value)


def test_gift_sem_nome_e_sem_id_e_recusado():
    cfg = _base()
    cfg["rules"]["gifts"] = [{"action": "xp", "xp": 1}]
    with pytest.raises(ConfigError) as exc:
        validate_config(cfg)
    assert "gift" in str(exc.value)


def test_cooldown_negativo_e_recusado():
    cfg = _base()
    cfg["rules"]["gifts"] = [{"gift": "Rose", "action": "xp", "cooldown": -1}]
    with pytest.raises(ConfigError):
        validate_config(cfg)


def test_render_scale_zero_ou_negativo_e_recusado():
    for ruim in (0, -1, 0.0):
        cfg = _base()
        cfg["app"]["render_scale"] = ruim
        with pytest.raises(ConfigError):
            validate_config(cfg)


def test_render_scale_absurdo_que_gera_janela_minuscula_e_recusado():
    cfg = _base()
    cfg["app"]["render_scale"] = 0.0001
    with pytest.raises(ConfigError) as exc:
        validate_config(cfg)
    assert "render_scale" in str(exc.value)


def test_username_placeholder_e_recusado():
    cfg = _base()
    cfg["tiktok"]["username"] = "@SEU_USUARIO"
    with pytest.raises(ConfigError):
        validate_config(cfg)


def test_secao_faltando_e_recusada():
    cfg = _base()
    del cfg["game"]
    with pytest.raises(ConfigError) as exc:
        validate_config(cfg)
    assert "game" in str(exc.value)


def test_defaults_sao_aplicados_em_campos_ausentes():
    cfg = _base()
    del cfg["game"]["max_hp"]
    cfg["game"]["zzz"] = 1
    validate_config(cfg)
    assert cfg["game"]["max_hp"] == 100


def test_like_rule_sem_every_valido_e_recusada():
    cfg = _base()
    cfg["rules"]["likes"] = [{"action": "xp", "every": 0}]
    with pytest.raises(ConfigError) as exc:
        validate_config(cfg)
    assert "every" in str(exc.value)


def test_arquivo_inexistente_levanta_erro_claro(tmp_path):
    with pytest.raises(ConfigError):
        load_config(tmp_path / "naoexiste.json")


def test_json_invalido_levanta_config_error(tmp_path):
    ruim = tmp_path / "config.json"
    ruim.write_text("{ isso nao e json }", encoding="utf-8")
    with pytest.raises(ConfigError):
        load_config(ruim)


def test_xp_per_level_zero_e_recusado():
    # Sem esta validacao o `while` de level up nunca termina e a LIVE congela.
    cfg = _base()
    cfg["game"]["xp_per_level"] = 0
    with pytest.raises(ConfigError) as exc:
        validate_config(cfg)
    assert "xp_per_level" in str(exc.value)


def test_velocidade_inicial_negativa_e_recusada():
    cfg = _base()
    cfg["game"]["initial_speed"] = -10
    with pytest.raises(ConfigError):
        validate_config(cfg)


def test_queue_max_size_zero_e_recusado():
    # queue.Queue trata maxsize <= 0 como fila infinita: o descarte do
    # anti-spam sumiria sem aviso.
    cfg = _base()
    cfg["app"]["queue_max_size"] = 0
    with pytest.raises(ConfigError) as exc:
        validate_config(cfg)
    assert "queue_max_size" in str(exc.value)


def test_scale_with_quantity_exige_max_multiplier():
    cfg = _base()
    cfg["rules"]["gifts"] = [
        {"gift": "Rose", "action": "xp", "xp": 1, "scale_with_quantity": True}
    ]
    with pytest.raises(ConfigError) as exc:
        validate_config(cfg)
    assert "max_multiplier" in str(exc.value)


def test_max_multiplier_zero_e_recusado():
    cfg = _base()
    cfg["rules"]["gifts"] = [
        {"gift": "Rose", "action": "xp", "xp": 1,
         "scale_with_quantity": True, "max_multiplier": 0}
    ]
    with pytest.raises(ConfigError):
        validate_config(cfg)
