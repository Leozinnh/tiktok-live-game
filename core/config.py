import json
from pathlib import Path
from typing import Any

from game.actions import known_actions

# Nomes de acao validos no config.json. Vem do registro real de acoes:
# adicionar uma acao em game/actions.py ja a habilita na configuracao.
ACOES_VALIDAS = known_actions()

SECOES_OBRIGATORIAS = ("app", "tiktok", "game", "rules")
SECOES_DE_REGRA = ("gifts", "comments", "likes", "follows", "shares")

# Menor janela aceitavel, em pixels. Abaixo disso a captura pelo OBS
# nao tem o que capturar.
JANELA_MINIMA = 240

# O config.json e entregue com este placeholder. O modo LIVE recusa; o
# modo teste aceita, porque nao conecta ao TikTok.
PLACEHOLDER_USERNAME = "@SEU_USUARIO"

DEFAULTS: dict[str, Any] = {
    "app": {
        "fps": 60,
        "window_width": 1080,
        "window_height": 1920,
        "render_scale": 1.0,
        "queue_max_size": 5000,
        "events_per_frame": 25,
        "feed_size": 6,
        "announce_ttl": 4.0,
    },
    "tiktok": {
        "username": "",
        "reconnect_seconds": 5,
        "reconnect_max_seconds": 60,
        "fetch_gift_info": True,
    },
    "game": {
        "max_hp": 100,
        "initial_hp": 100,
        "initial_xp": 0,
        "initial_level": 1,
        "initial_speed": 220,
        "xp_per_level": 100,
        "xp_level_step": 25,
        "base_enemy_damage": 5,
        "intent_half_life": 1.5,
        "intent_accel": 1800.0,
        "intent_max_speed": 420.0,
        "intent_friction": 6.0,
    },
    "limits": {
        "max_enemies": 40,
        "action_budget": {"spawn_enemy": 4.0, "boss": 0.5, "special": 1.0, "mega": 0.5},
    },
}


class ConfigError(ValueError):
    """Configuracao ausente, malformada ou com valor invalido."""


def _merge_defaults(config: dict, defaults: dict) -> None:
    for chave, valor in defaults.items():
        if chave not in config:
            config[chave] = json.loads(json.dumps(valor))
        elif isinstance(valor, dict) and isinstance(config[chave], dict):
            _merge_defaults(config[chave], valor)


def _exigir_numero(valor: Any, onde: str, campo: str, minimo: float = 0.0) -> None:
    if not isinstance(valor, (int, float)) or isinstance(valor, bool):
        raise ConfigError(f"{onde}: campo '{campo}' precisa ser numero, veio {valor!r}.")
    if valor < minimo:
        raise ConfigError(f"{onde}: campo '{campo}' nao pode ser negativo (veio {valor}).")


def _validar_regra(regra: dict, onde: str) -> None:
    if not isinstance(regra, dict):
        raise ConfigError(f"{onde}: cada regra precisa ser um objeto JSON.")

    acao = regra.get("action")
    if acao not in ACOES_VALIDAS:
        raise ConfigError(
            f"{onde}: acao desconhecida {acao!r}. "
            f"Validas: {', '.join(sorted(ACOES_VALIDAS))}."
        )

    for campo in ("cooldown", "per_user_cooldown", "duration"):
        if campo in regra:
            _exigir_numero(regra[campo], onde, campo)

    for campo in ("xp", "min_quantity", "max_multiplier"):
        if campo in regra:
            _exigir_numero(regra[campo], onde, campo)

    # `amount` pode ser negativo: a regra de "esquerda" manda amount -1 e o
    # handler de `steer` usa o sinal como direcao.
    if "amount" in regra and not isinstance(regra["amount"], (int, float)):
        raise ConfigError(f"{onde}: campo 'amount' precisa ser numero, veio {regra['amount']!r}.")
    if "amount" in regra and isinstance(regra["amount"], bool):
        raise ConfigError(f"{onde}: campo 'amount' precisa ser numero, veio {regra['amount']!r}.")


def validate_config(config: dict, exigir_username: bool = True) -> None:
    """Valida e completa a configuracao. Levanta ConfigError se algo estiver errado.

    `exigir_username=False` aceita o config.json recem-clonado, que ainda
    traz o placeholder. O modo teste (`main.py --test`) NAO conecta ao
    TikTok, entao nao precisa de username real; o modo LIVE passa
    `exigir_username=True` e recusa o placeholder.
    """
    if not isinstance(config, dict):
        raise ConfigError("A configuracao precisa ser um objeto JSON na raiz.")

    faltando = [s for s in SECOES_OBRIGATORIAS if s not in config]
    if faltando:
        raise ConfigError(f"Configuracao incompleta. Faltando: {', '.join(faltando)}.")

    _merge_defaults(config, DEFAULTS)

    username = str(config["tiktok"].get("username", "")).strip()
    if exigir_username and (not username or username == PLACEHOLDER_USERNAME):
        raise ConfigError(
            "Edite config.json e coloque o username real da LIVE em tiktok.username."
        )
    config["tiktok"]["username"] = username

    app = config["app"]
    for campo in ("window_width", "window_height"):
        valor = app.get(campo)
        _exigir_numero(valor, "app", campo, minimo=1)
        if valor < JANELA_MINIMA:
            raise ConfigError(
                f"app: campo '{campo}' precisa ser pelo menos {JANELA_MINIMA}px (veio {valor})."
            )

    escala = app.get("render_scale", 1.0)
    _exigir_numero(escala, "app", "render_scale", minimo=0.0)
    if escala <= 0:
        raise ConfigError(f"app: 'render_scale' precisa ser maior que zero (veio {escala}).")
    largura_final = app["window_width"] * escala
    altura_final = app["window_height"] * escala
    if largura_final < JANELA_MINIMA or altura_final < JANELA_MINIMA:
        raise ConfigError(
            f"app: 'render_scale' {escala} gera uma janela de "
            f"{largura_final:.0f}x{altura_final:.0f}px, pequena demais para captura."
        )

    _exigir_numero(app.get("fps"), "app", "fps", minimo=1)

    rules = config["rules"]
    if not isinstance(rules, dict):
        raise ConfigError("'rules' precisa ser um objeto JSON.")

    for secao in SECOES_DE_REGRA:
        regras = rules.get(secao, [])
        if not isinstance(regras, list):
            raise ConfigError(f"rules.{secao} precisa ser uma lista.")
        for i, regra in enumerate(regras):
            onde = f"rules.{secao}[{i}]"
            if secao == "gifts":
                if not regra.get("gift") and not regra.get("gift_id"):
                    raise ConfigError(f"{onde}: precisa de 'gift' (nome) ou 'gift_id'.")
                nome = regra.get("gift") or regra.get("gift_id")
                onde = f"rules.{secao}[{i}] (gift={nome})"
            elif secao == "comments":
                if not regra.get("contains"):
                    raise ConfigError(f"{onde}: precisa de 'contains'.")
                onde = f"rules.{secao}[{i}] (contains={regra['contains']})"
            elif secao == "likes":
                every = regra.get("every")
                if not isinstance(every, int) or isinstance(every, bool) or every <= 0:
                    raise ConfigError(
                        f"{onde}: 'every' precisa ser um inteiro maior que zero (veio {every!r})."
                    )
            _validar_regra(regra, onde)

    limites = config.get("limits", {})
    if "max_enemies" in limites:
        _exigir_numero(limites["max_enemies"], "limits", "max_enemies", minimo=1)


def load_config(path: str | Path, exigir_username: bool = True) -> dict:
    arquivo = Path(path)
    if not arquivo.exists():
        raise ConfigError(f"Configuracao nao encontrada: {arquivo}")

    try:
        with arquivo.open("r", encoding="utf-8") as f:
            config = json.load(f)
    except json.JSONDecodeError as erro:
        raise ConfigError(
            f"{arquivo} nao e um JSON valido: linha {erro.lineno}, coluna {erro.colno} ({erro.msg})."
        ) from erro

    validate_config(config, exigir_username=exigir_username)
    return config
