import json
from pathlib import Path


def load_config(path: str) -> dict:
    file = Path(path)
    if not file.exists():
        raise FileNotFoundError(f"Configuração não encontrada: {file}")

    with file.open("r", encoding="utf-8") as f:
        config = json.load(f)

    validate_config(config)
    return config


def validate_config(config: dict):
    required = ["app", "tiktok", "game", "rules"]
    missing = [key for key in required if key not in config]
    if missing:
        raise ValueError(f"Configuração incompleta. Faltando: {missing}")

    username = config["tiktok"].get("username", "").strip()
    if not username or username == "@SEU_USUARIO":
        raise ValueError(
            "Edite config.json e coloque o username real da LIVE em tiktok.username."
        )
