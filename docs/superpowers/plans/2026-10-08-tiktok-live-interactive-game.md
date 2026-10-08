# TikTok LIVE Interactive Game — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Transformar o protótipo existente em um jogo interativo vertical 9:16, capturável pelo OBS, que reage em tempo real a comentários, presentes, likes, follows e shares de uma LIVE real do TikTok.

**Architecture:** Pipeline em camadas com dependência unidirecional `adapters → core → game → ui`. O núcleo (`core/`, `game/`) não importa `pygame` nem `TikTokLive`, então é testável sem abrir janela e sem LIVE. O adaptador de eventos é trocável (real ou simulado) por trás do mesmo protocolo, e o renderer só lê o estado do jogo.

**Tech Stack:** Python 3.14, `pygame-ce` 2.5.8 (não `pygame` — ver Restrições Globais), `TikTokLive` 7.0.1, `pytest`.

**Spec:** `docs/superpowers/specs/2026-10-08-tiktok-live-interactive-game-design.md`

## Global Constraints

- **`pygame` NÃO tem wheel para cp314 e a instalação falha.** Usar `pygame-ce==2.5.8`, que publica wheel cp314 e fornece o pacote top-level `pygame`. Nunca instalar os dois juntos.
- `TikTokLive==7.0.1`. Import correto: **`from TikTokLive import TikTokLiveClient`**. `from TikTokLive.client import TikTokLiveClient` **falha** (o `__init__.py` tem 0 bytes).
- `core/` e `game/` **não podem** importar `pygame` nem `TikTokLive`. `ui/` nunca escreve no estado do jogo.
- Resolução lógica de projeto: **1080x1920**. `render_scale` (default `1.0`) multiplica para o tamanho da janela.
- Todos os textos visíveis ao público em **português**. Comentários e docstrings em português.
- Nomes de ação válidos (exatamente estes 12): `xp`, `heal`, `damage`, `run`, `jump`, `speed`, `shield`, `rage`, `spawn_enemy`, `special`, `boss`, `mega`.
- Tipos de evento (exatamente estes): `comment`, `gift`, `like`, `follow`, `share`, `system`.
- Toda validação de config deve **recusar a inicialização** com mensagem que aponta o presente e o campo com erro.
- Latência do TikTok é de 10–30 s: a meia-vida do vetor de intenção é **1,5 s** (default configurável), não 0,35 s.
- Commits em português, terminando com `Co-Authored-By: Claude Code <noreply@anthropic.com>`.

## Review Focus

Inputs e condições que a spec implica mas nenhum teste óbvio cobre — cada linha vira teste na tarefa dona do código:

1. **`event.user` pode ser `None`** no `LikeEvent` (o TikTok limita likes por usuário após ~10–20). Um like sem usuário não pode levantar exceção nem virar actor `"None"`. → Task 12, 10.
2. **Presente sem `gift_id` e sem nome casando** deve ser ignorado em silêncio, sem ação nem log de erro. → Task 10.
3. **`config.json` com `render_scale` absurdo** (0, negativo, ou que gere janela < 1 px) não pode abrir uma janela inválida nem dividir por zero. → Task 4, 14.
4. **Fila de eventos sob rajada contínua** deve descartar o **mais antigo** e nunca bloquear a thread do adapter. → Task 3.
5. **Comentário com emoji, acento ou caixa alta** (`"CORRE!!!"`, `"corré"`) deve casar a regra `"corre"`. → Task 10.

---

## Estrutura de arquivos

| Arquivo | Responsabilidade |
|---|---|
| `requirements.txt` | Dependências fixadas |
| `core/events.py` | `LiveEvent` — contrato único adapter→núcleo |
| `core/event_queue.py` | Fila thread-safe com descarte e estatísticas |
| `core/config.py` | Carga, merge de defaults e **validação de schema** |
| `core/ratelimit.py` | Cooldowns (regra, usuário) e orçamento global |
| `core/logging_setup.py` | `app.log` com rotação + `events.jsonl` |
| `core/rules.py` | `RuleEngine` — traduz evento em ação |
| `game/state.py` | `GameState` — dados puros, serializável |
| `game/entities.py` | `Character`, `Enemy`, `Boss` |
| `game/effects.py` | Efeitos temporários e fila de anúncios |
| `game/actions.py` | `ACTION_REGISTRY` — nome → função |
| `game/engine.py` | Simulação e despacho |
| `adapters/base.py` | Protocolo `LiveAdapter` |
| `adapters/simulated.py` | Modo teste (REPL, script, burst) |
| `adapters/tiktok_live.py` | Integração real |
| `ui/theme.py` | Cores, fontes, medidas |
| `ui/widgets.py` | Cache de texto, barra, painel |
| `ui/hud.py` | Topo: HP/XP/level |
| `ui/feed.py` | Rodapé: eventos recentes |
| `ui/overlay.py` | Toasts e banners |
| `ui/arena.py` | Personagem, inimigos, chão |
| `ui/pygame_ui.py` | Janela e orquestração do frame |
| `main.py` | CLI e game loop |
| `config.json` | Toda a configuração |
| `README.md` | Instalação, OBS, limitações |
| `tests/test_*.py` | Testes do núcleo |

---

### Task 1: Ambiente e dependências

**Files:**
- Modify: `requirements.txt`
- Create: `tests/__init__.py`, `pytest.ini`
- Modify: `.gitignore`

**Interfaces:**
- Consumes: nada
- Produces: ambiente virtual funcionando com `pygame`, `TikTokLive` e `pytest` importáveis

- [ ] **Step 1: Criar o venv**

```powershell
cd C:\Users\leona\Downloads\tiktok_live_interactive_game
py -3.14 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
```

- [ ] **Step 2: Escrever `requirements.txt`**

```
pygame-ce==2.5.8
TikTokLive==7.0.1

# Desenvolvimento
pytest==8.3.4
```

> `pygame-ce` instala o pacote `pygame`. Não adicionar `pygame` — os dois escrevem no mesmo diretório e um sobrescreve o outro.

- [ ] **Step 3: Instalar**

```powershell
pip install -r requirements.txt
```

Esperado: instala sem compilar nada. Se aparecer `No matching distribution found for pygame`, o `requirements.txt` ainda tem `pygame` em vez de `pygame-ce`.

- [ ] **Step 4: Verificar os imports**

```powershell
python -c "import pygame; print('pygame', pygame.version.ver)"
python -c "from TikTokLive import TikTokLiveClient; print('TikTokLive OK')"
python -c "import pytest; print('pytest', pytest.__version__)"
```

Esperado: `pygame 2.5.8`, `TikTokLive OK`, `pytest 8.3.4`.

- [ ] **Step 5: Criar `pytest.ini`**

```ini
[pytest]
testpaths = tests
python_files = test_*.py
addopts = -q
```

- [ ] **Step 6: Atualizar `.gitignore`**

```
.venv/
__pycache__/
*.pyc
.pytest_cache/
logs/
.idea/
.vscode/
```

> `logs/` continua ignorado: são artefatos de execução, não código.

- [ ] **Step 7: Criar `tests/__init__.py` vazio e commitar**

```bash
git add requirements.txt pytest.ini .gitignore tests/__init__.py
git commit -m "Configura ambiente com pygame-ce e pytest"
```

---

### Task 2: `core/events.py` — o contrato de evento

**Files:**
- Modify: `core/events.py`
- Test: `tests/test_events.py`

**Interfaces:**
- Consumes: nada
- Produces: `EventType` (enum de str) e `LiveEvent` com os campos `type, username, display_name, text, gift_name, gift_id, quantity, like_delta, like_total, raw, timestamp` e o método `actor() -> str`

- [ ] **Step 1: Escrever o teste que falha**

```python
from core.events import EventType, LiveEvent


def test_actor_prefere_display_name():
    e = LiveEvent(type=EventType.GIFT, username="joao123", display_name="João")
    assert e.actor() == "João"


def test_actor_cai_para_username():
    e = LiveEvent(type=EventType.GIFT, username="joao123")
    assert e.actor() == "joao123"


def test_actor_sem_nada_nao_retorna_none_como_texto():
    e = LiveEvent(type=EventType.LIKE)
    assert e.actor() == "desconhecido"
    assert "None" not in e.actor()


def test_like_sem_usuario_nao_quebra():
    # O TikTok limita likes por usuario; depois disso event.user pode vir None.
    e = LiveEvent(type=EventType.LIKE, like_delta=3, like_total=120)
    assert e.actor() == "desconhecido"
    assert e.like_total == 120


def test_tipo_e_comparavel_com_string():
    assert LiveEvent(type=EventType.GIFT).type == "gift"
```

- [ ] **Step 2: Rodar e ver falhar**

Run: `pytest tests/test_events.py -v`
Esperado: FAIL — `ImportError: cannot import name 'EventType'`

- [ ] **Step 3: Implementar**

```python
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any


class EventType(str, Enum):
    """Tipos de evento que o nucleo entende.

    Herda de str para que EventType.GIFT == "gift", o que mantem
    comparacoes e serializacao simples.
    """

    COMMENT = "comment"
    GIFT = "gift"
    LIKE = "like"
    FOLLOW = "follow"
    SHARE = "share"
    SYSTEM = "system"


@dataclass(slots=True)
class LiveEvent:
    """Formato interno da aplicacao.

    O adapter converte o evento externo para este formato. Nada fora do
    adapter le o campo `raw`, o que impede o formato do TikTok de vazar
    para o resto do sistema.
    """

    type: EventType
    username: str = ""
    display_name: str = ""
    text: str = ""
    gift_name: str = ""
    gift_id: str | None = None
    quantity: int = 1
    like_delta: int = 0
    like_total: int = 0
    raw: Any = None
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))

    def actor(self) -> str:
        """Nome de exibicao para a tela. Nunca retorna a string 'None'."""
        return self.display_name or self.username or "desconhecido"
```

- [ ] **Step 4: Rodar e ver passar**

Run: `pytest tests/test_events.py -v`
Esperado: 5 passed

- [ ] **Step 5: Commitar**

```bash
git add core/events.py tests/test_events.py
git commit -m "Adiciona EventType e LiveEvent com like_delta e like_total"
```

---

### Task 3: `core/event_queue.py` — fila com estatísticas corretas

**Files:**
- Modify: `core/event_queue.py`
- Test: `tests/test_event_queue.py`

**Interfaces:**
- Consumes: `core.events.LiveEvent`
- Produces: `EventQueue(maxsize)` com `put(event)`, `get_nowait() -> LiveEvent | None`, `drain(limit) -> list[LiveEvent]`, `size() -> int` e as propriedades `dropped`, `accepted`

**Contexto:** o código atual incrementa `dropped` só em um dos dois caminhos de descarte, então as estatísticas mentem. A fila cheia deve descartar o **mais antigo** — num jogo ao vivo o evento recente vale mais.

- [ ] **Step 1: Escrever o teste que falha**

```python
from core.event_queue import EventQueue
from core.events import EventType, LiveEvent


def _ev(n: int) -> LiveEvent:
    return LiveEvent(type=EventType.COMMENT, username=f"u{n}", text=str(n))


def test_put_e_get():
    q = EventQueue(maxsize=10)
    q.put(_ev(1))
    assert q.get_nowait().text == "1"


def test_get_vazio_retorna_none():
    assert EventQueue(maxsize=10).get_nowait() is None


def test_fila_cheia_descarta_o_mais_antigo():
    q = EventQueue(maxsize=3)
    for i in range(5):
        q.put(_ev(i))
    restantes = [q.get_nowait().text for _ in range(3)]
    assert restantes == ["2", "3", "4"]


def test_contador_de_descarte_e_exato():
    q = EventQueue(maxsize=3)
    for i in range(5):
        q.put(_ev(i))
    assert q.dropped == 2
    assert q.accepted == 3


def test_nunca_levanta_excecao_com_fila_cheia():
    q = EventQueue(maxsize=1)
    for i in range(100):
        q.put(_ev(i))  # nao pode levantar


def test_drain_respeita_o_limite():
    q = EventQueue(maxsize=100)
    for i in range(50):
        q.put(_ev(i))
    lote = q.drain(limit=20)
    assert len(lote) == 20
    assert q.size() == 30


def test_drain_pega_o_mais_antigo_primeiro():
    q = EventQueue(maxsize=100)
    for i in range(5):
        q.put(_ev(i))
    assert [e.text for e in q.drain(3)] == ["0", "1", "2"]
```

- [ ] **Step 2: Rodar e ver falhar**

Run: `pytest tests/test_event_queue.py -v`
Esperado: FAIL — `AttributeError: 'EventQueue' object has no attribute 'accepted'`

- [ ] **Step 3: Implementar**

```python
import logging
import queue

from core.events import LiveEvent

logger = logging.getLogger(__name__)


class EventQueue:
    """Fila thread-safe entre o adapter e o loop do jogo.

    O adapter escreve de outra thread; o Pygame consome na thread principal.
    Nenhum estado de jogo e compartilhado entre as duas.
    """

    def __init__(self, maxsize: int = 5000):
        self._queue: queue.Queue[LiveEvent] = queue.Queue(maxsize=maxsize)
        self._dropped = 0
        self._accepted = 0

    def put(self, event: LiveEvent) -> None:
        """Enfileira sem nunca bloquear a thread do adapter."""
        try:
            self._queue.put_nowait(event)
            self._accepted += 1
            return
        except queue.Full:
            pass

        # Fila cheia: descarta o MAIS ANTIGO. Num jogo ao vivo o evento
        # recente vale mais que o antigo.
        try:
            self._queue.get_nowait()
            self._queue.put_nowait(event)
            self._accepted += 1
        except queue.Empty:
            pass
        except queue.Full:
            pass
        self._dropped += 1

    def get_nowait(self) -> LiveEvent | None:
        try:
            return self._queue.get_nowait()
        except queue.Empty:
            return None

    def drain(self, limit: int) -> list[LiveEvent]:
        """Retira ate `limit` eventos, do mais antigo para o mais novo."""
        lote: list[LiveEvent] = []
        for _ in range(max(0, limit)):
            evento = self.get_nowait()
            if evento is None:
                break
            lote.append(evento)
        return lote

    def size(self) -> int:
        return self._queue.qsize()

    @property
    def dropped(self) -> int:
        return self._dropped

    @property
    def accepted(self) -> int:
        return self._accepted
```

- [ ] **Step 4: Rodar e ver passar**

Run: `pytest tests/test_event_queue.py -v`
Esperado: 7 passed

- [ ] **Step 5: Commitar**

```bash
git add core/event_queue.py tests/test_event_queue.py
git commit -m "Corrige contagem de descarte e adiciona drain a EventQueue"
```

---

### Task 4: `core/config.py` — validação de schema

**Files:**
- Modify: `core/config.py`
- Test: `tests/test_config.py`

**Interfaces:**
- Consumes: `game.actions.known_actions()` — nesta tarefa use um `frozenset` local `ACOES_VALIDAS`; a Task 8 troca por import
- Produces: `ConfigError`, `load_config(path) -> dict`, `validate_config(config) -> None`, `DEFAULTS: dict`

**Contexto:** hoje só as chaves de topo são conferidas, então `"action": "corree"` vira um warning no meio da LIVE. Sem validação, "adicionar presente sem tocar em Python" não é seguro.

- [ ] **Step 1: Escrever o teste que falha**

```python
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
```

- [ ] **Step 2: Rodar e ver falhar**

Run: `pytest tests/test_config.py -v`
Esperado: FAIL — `ImportError: cannot import name 'ConfigError'`

- [ ] **Step 3: Implementar**

```python
import json
from pathlib import Path
from typing import Any

# A Task 8 substitui isto por `from game.actions import known_actions`.
ACOES_VALIDAS = frozenset({
    "xp", "heal", "damage", "run", "jump", "speed",
    "shield", "rage", "spawn_enemy", "special", "boss", "mega",
})

SECOES_OBRIGATORIAS = ("app", "tiktok", "game", "rules")
SECOES_DE_REGRA = ("gifts", "comments", "likes", "follows", "shares")

# Menor janela aceitavel, em pixels. Abaixo disso a captura pelo OBS
# nao tem o que capturar.
JANELA_MINIMA = 240

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

    for campo in ("amount", "xp", "min_quantity", "max_multiplier"):
        if campo in regra:
            _exigir_numero(regra[campo], onde, campo)


def validate_config(config: dict) -> None:
    """Valida e completa a configuracao. Levanta ConfigError se algo estiver errado."""
    if not isinstance(config, dict):
        raise ConfigError("A configuracao precisa ser um objeto JSON na raiz.")

    faltando = [s for s in SECOES_OBRIGATORIAS if s not in config]
    if faltando:
        raise ConfigError(f"Configuracao incompleta. Faltando: {', '.join(faltando)}.")

    _merge_defaults(config, DEFAULTS)

    username = str(config["tiktok"].get("username", "")).strip()
    if not username or username == "@SEU_USUARIO":
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
                    raise ConfigError(
                        f"{onde}: precisa de 'gift' (nome) ou 'gift_id'."
                    )
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


def load_config(path: str | Path) -> dict:
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

    validate_config(config)
    return config
```

- [ ] **Step 4: Rodar e ver passar**

Run: `pytest tests/test_config.py -v`
Esperado: 12 passed

- [ ] **Step 5: Commitar**

```bash
git add core/config.py tests/test_config.py
git commit -m "Adiciona validacao de schema na configuracao"
```

---

### Task 5: `core/ratelimit.py` — as quatro camadas

**Files:**
- Create: `core/ratelimit.py`
- Test: `tests/test_ratelimit.py`

**Interfaces:**
- Consumes: nada
- Produces: `RateLimiter(action_budget: dict[str, float] | None = None, now_fn=time.monotonic)` com `allow_rule(rule_key, cooldown, actor, per_user_cooldown) -> bool` e `allow_action(action) -> bool`

**Contexto:** cooldown único não segura "50 pessoas mandam o mesmo presente ao mesmo tempo". A quarta camada (teto de entidades) fica no `GameEngine`, na Task 8.

- [ ] **Step 1: Escrever o teste que falha**

```python
from core.ratelimit import RateLimiter


class Relogio:
    """Relogio controlado para testar tempo sem dormir."""

    def __init__(self):
        self.t = 0.0

    def __call__(self) -> float:
        return self.t

    def avanca(self, dt: float) -> None:
        self.t += dt


def test_cooldown_de_regra_bloqueia_dentro_da_janela():
    relogio = Relogio()
    rl = RateLimiter(now_fn=relogio)
    assert rl.allow_rule("gift:Rose", cooldown=2.0, actor="joao", per_user_cooldown=0.0)
    relogio.avanca(1.0)
    assert not rl.allow_rule("gift:Rose", cooldown=2.0, actor="joao", per_user_cooldown=0.0)


def test_cooldown_de_regra_libera_depois():
    relogio = Relogio()
    rl = RateLimiter(now_fn=relogio)
    rl.allow_rule("gift:Rose", 2.0, "joao", 0.0)
    relogio.avanca(2.1)
    assert rl.allow_rule("gift:Rose", 2.0, "joao", 0.0)


def test_cooldown_por_usuario_nao_afeta_outro_usuario():
    relogio = Relogio()
    rl = RateLimiter(now_fn=relogio)
    assert rl.allow_rule("gift:Rose", 0.0, "joao", per_user_cooldown=5.0)
    # Maria nao pode ser punida pelo spam do Joao.
    assert rl.allow_rule("gift:Rose", 0.0, "maria", per_user_cooldown=5.0)


def test_cooldown_por_usuario_bloqueia_o_mesmo_usuario():
    relogio = Relogio()
    rl = RateLimiter(now_fn=relogio)
    rl.allow_rule("gift:Rose", 0.0, "joao", 5.0)
    assert not rl.allow_rule("gift:Rose", 0.0, "joao", 5.0)


def test_ator_vazio_nao_compartilha_balde_com_outro_vazio():
    relogio = Relogio()
    rl = RateLimiter(now_fn=relogio)
    assert rl.allow_rule("comment:direita", 0.0, "", 1.0)
    assert rl.allow_rule("comment:direita", 0.0, "", 1.0)


def test_orcamento_global_limita_rajada():
    relogio = Relogio()
    rl = RateLimiter(action_budget={"spawn_enemy": 3.0}, now_fn=relogio)
    permitidos = sum(1 for _ in range(50) if rl.allow_action("spawn_enemy"))
    assert permitidos == 3


def test_orcamento_global_recarrega_com_o_tempo():
    relogio = Relogio()
    rl = RateLimiter(action_budget={"spawn_enemy": 3.0}, now_fn=relogio)
    for _ in range(3):
        rl.allow_action("spawn_enemy")
    assert not rl.allow_action("spawn_enemy")
    relogio.avanca(1.1)
    assert rl.allow_action("spawn_enemy")


def test_acao_sem_orcamento_configurado_e_sempre_permitida():
    rl = RateLimiter(action_budget={"spawn_enemy": 1.0}, now_fn=Relogio())
    assert all(rl.allow_action("xp") for _ in range(100))


def test_rajada_de_50_da_mesma_regra_nao_trava():
    relogio = Relogio()
    rl = RateLimiter(now_fn=relogio)
    permitidos = sum(
        1 for _ in range(50) if rl.allow_rule("gift:Cap", 2.0, f"u{i}", 0.0)
    )
    assert permitidos == 1
```

- [ ] **Step 2: Rodar e ver falhar**

Run: `pytest tests/test_ratelimit.py -v`
Esperado: FAIL — `ModuleNotFoundError: No module named 'core.ratelimit'`

- [ ] **Step 3: Implementar**

```python
import time
from collections import defaultdict, deque
from typing import Callable

# Um ator sem nome (like anonimo) nao pode compartilhar balde com outro
# ator sem nome, senao um usuario sem nome silencia todos os outros.
_ATOR_ANONIMO = "\x00anonimo"

JANELA_ORCAMENTO = 1.0


class RateLimiter:
    """Controle de spam em camadas.

    Camada 1: cooldown da regra       - rajada repetida da mesma regra.
    Camada 2: cooldown por usuario    - um usuario monopolizando.
    Camada 3: orcamento global        - muitos usuarios na mesma acao.

    A camada 4 (teto de entidades) vive no GameEngine, porque depende do
    estado do jogo, nao do tempo.
    """

    def __init__(
        self,
        action_budget: dict[str, float] | None = None,
        now_fn: Callable[[], float] = time.monotonic,
    ):
        self._now = now_fn
        self._budget = dict(action_budget or {})
        self._regra: dict[str, float] = {}
        self._usuario: dict[tuple[str, str], float] = {}
        self._janelas: dict[str, deque[float]] = defaultdict(deque)

    def allow_rule(
        self,
        rule_key: str,
        cooldown: float,
        actor: str,
        per_user_cooldown: float,
    ) -> bool:
        """Camadas 1 e 2. Retorna True se a regra pode disparar agora."""
        agora = self._now()

        if cooldown > 0:
            ultimo = self._regra.get(rule_key)
            if ultimo is not None and agora - ultimo < cooldown:
                return False

        ator = actor.strip() or _ATOR_ANONIMO
        chave = (rule_key, ator)
        if per_user_cooldown > 0:
            ultimo = self._usuario.get(chave)
            if ultimo is not None and agora - ultimo < per_user_cooldown:
                return False

        if cooldown > 0:
            self._regra[rule_key] = agora
        if per_user_cooldown > 0:
            self._usuario[chave] = agora
        return True

    def allow_action(self, action: str) -> bool:
        """Camada 3. Janela deslizante de 1s por acao."""
        limite = self._budget.get(action)
        if limite is None:
            return True

        agora = self._now()
        janela = self._janelas[action]

        while janela and agora - janela[0] >= JANELA_ORCAMENTO:
            janela.popleft()

        if len(janela) >= limite:
            return False

        janela.append(agora)
        return True
```

- [ ] **Step 4: Rodar e ver passar**

Run: `pytest tests/test_ratelimit.py -v`
Esperado: 9 passed

- [ ] **Step 5: Commitar**

```bash
git add core/ratelimit.py tests/test_ratelimit.py
git commit -m "Adiciona RateLimiter com cooldown de regra, por usuario e orcamento global"
```

---

### Task 6: `game/entities.py` e `game/state.py`

**Files:**
- Create: `game/entities.py`, `game/state.py`
- Modify: `game/engine.py` (remover `Enemy` e `GameState` daqui — ficam só reexportados até a Task 8)
- Test: `tests/test_entities.py`

**Interfaces:**
- Consumes: nada
- Produces: `Character`, `Enemy`, `Boss` (dataclasses); `GameState` com campos `hp, max_hp, xp, level, speed, base_speed, character, enemies, boss, effects, announcements, total_gifts, total_likes, total_followers, total_shares` e método `to_dict() -> dict`

- [ ] **Step 1: Escrever o teste que falha**

```python
import math

from game.entities import Boss, Character, Enemy
from game.state import GameState


def test_inimigo_dentro_do_raio_atinge_o_personagem():
    inimigo = Enemy(x=105.0, y=900.0)
    assert inimigo.reached(100.0, 900.0, raio=30.0)


def test_inimigo_longe_nao_atinge():
    assert not Enemy(x=500.0, y=900.0).reached(100.0, 900.0, raio=30.0)


def test_boss_comeca_com_hp_cheio_e_e_um_inimigo():
    boss = Boss(x=540.0, y=600.0, hp=500, max_hp=500)
    assert boss.is_alive()
    assert boss.hp_fraction() == 1.0
    assert isinstance(boss, Enemy)


def test_boss_meio_vivo():
    boss = Boss(x=0, y=0, hp=250, max_hp=500)
    assert math.isclose(boss.hp_fraction(), 0.5)


def test_boss_com_hp_zero_esta_morto():
    assert not Boss(x=0, y=0, hp=0, max_hp=500).is_alive()


def test_character_tem_estado_de_pulo():
    c = Character()
    assert c.y_offset == 0.0


def test_gamestate_to_dict_e_serializavel_em_json():
    import json

    estado = GameState()
    estado.enemies.append(Enemy(x=1.0, y=2.0))
    d = estado.to_dict()
    json.dumps(d)  # nao pode levantar
    assert d["hp"] == estado.hp
    assert len(d["enemies"]) == 1


def test_gamestate_to_dict_nao_expoe_objetos_do_pygame():
    d = GameState().to_dict()
    for chave, valor in d.items():
        assert not type(valor).__module__.startswith("pygame"), chave
```

- [ ] **Step 2: Rodar e ver falhar**

Run: `pytest tests/test_entities.py -v`
Esperado: FAIL — `ModuleNotFoundError: No module named 'game.entities'`

- [ ] **Step 3: Implementar `game/entities.py`**

```python
import math
from dataclasses import dataclass


@dataclass
class Enemy:
    """Inimigo comum. Desce em direcao ao personagem."""

    x: float
    y: float
    hp: int = 30
    speed: float = 70.0
    radius: float = 22.0

    def reached(self, alvo_x: float, alvo_y: float, raio: float = 30.0) -> bool:
        return math.dist((self.x, self.y), (alvo_x, alvo_y)) <= raio

    def is_alive(self) -> bool:
        return self.hp > 0


@dataclass
class Boss(Enemy):
    """Inimigo grande, com barra de HP propria. Invoca inimigos comuns."""

    hp: int = 500
    max_hp: int = 500
    speed: float = 35.0
    radius: float = 60.0
    summon_every: float = 3.0
    since_summon: float = 0.0

    def hp_fraction(self) -> float:
        if self.max_hp <= 0:
            return 0.0
        return max(0.0, min(1.0, self.hp / self.max_hp))


@dataclass
class Character:
    """O personagem controlado pelo publico."""

    x: float = 540.0
    y: float = 1400.0
    vx: float = 0.0
    y_offset: float = 0.0
    radius: float = 34.0
    facing: int = 1
```

- [ ] **Step 4: Implementar `game/state.py`**

```python
from dataclasses import dataclass, field

from game.entities import Boss, Character, Enemy


@dataclass
class GameState:
    """Estado do jogo. Dados puros: nenhum import de pygame.

    `to_dict()` existe para que um renderer futuro (navegador, Unity) possa
    consumir o mesmo estado sem que a logica do jogo mude.
    """

    hp: int = 100
    max_hp: int = 100
    xp: int = 0
    level: int = 1
    speed: float = 220.0
    base_speed: float = 220.0

    character: Character = field(default_factory=Character)
    enemies: list[Enemy] = field(default_factory=list)
    boss: Boss | None = None

    # Preenchidos pela Task 7.
    effects: object | None = None
    announcements: object | None = None

    total_gifts: int = 0
    total_likes: int = 0
    total_followers: int = 0
    total_shares: int = 0

    def to_dict(self) -> dict:
        return {
            "hp": self.hp,
            "max_hp": self.max_hp,
            "xp": self.xp,
            "level": self.level,
            "speed": self.speed,
            "character": {
                "x": self.character.x,
                "y": self.character.y,
                "y_offset": self.character.y_offset,
                "facing": self.character.facing,
            },
            "enemies": [
                {"x": e.x, "y": e.y, "hp": e.hp, "radius": e.radius}
                for e in self.enemies
            ],
            "boss": (
                None
                if self.boss is None
                else {
                    "x": self.boss.x,
                    "y": self.boss.y,
                    "hp": self.boss.hp,
                    "max_hp": self.boss.max_hp,
                }
            ),
            "total_gifts": self.total_gifts,
            "total_likes": self.total_likes,
            "total_followers": self.total_followers,
            "total_shares": self.total_shares,
        }
```

- [ ] **Step 5: Rodar e ver passar**

Run: `pytest tests/test_entities.py -v`
Esperado: 8 passed

> `game/engine.py` ainda tem as suas próprias classes `Enemy`/`GameState` antigas. Não as remova agora — a Task 8 reescreve o arquivo inteiro. Isso mantém a árvore de commits sempre verde.

- [ ] **Step 6: Commitar**

```bash
git add game/entities.py game/state.py tests/test_entities.py
git commit -m "Extrai entidades e GameState para modulos proprios"
```

---

### Task 7: `game/effects.py` — efeitos e anúncios

**Files:**
- Create: `game/effects.py`
- Test: `tests/test_effects.py`

**Interfaces:**
- Consumes: nada
- Produces: `EffectSet(now_fn)` com `activate(name, duration)`, `active(name) -> bool`, `remaining(name) -> float`, `expire()`; `Announcement` (dataclass); `AnnouncementQueue(now_fn, max_size)` com `push(kind, actor, text, detail="", icon="", ttl=4.0, big=False)`, `active() -> list[Announcement]`, `expire()`

**Contexto:** os anúncios são **dados do jogo**, não da UI — assim um renderer futuro mostra os mesmos avisos sem reimplementar "o que merece destaque". Duração de efeito é **empilhável pelo maior fim**, não somada: dois escudos de 5 s não dão 10 s.

- [ ] **Step 1: Escrever o teste que falha**

```python
from game.effects import AnnouncementQueue, EffectSet


class Relogio:
    def __init__(self):
        self.t = 0.0

    def __call__(self) -> float:
        return self.t

    def avanca(self, dt: float) -> None:
        self.t += dt


def test_efeito_esta_ativo_enquanto_dentro_da_duracao():
    r = Relogio()
    e = EffectSet(now_fn=r)
    e.activate("shield", 5.0)
    assert e.active("shield")
    r.avanca(5.1)
    assert not e.active("shield")


def test_efeito_nao_ativado_esta_inativo():
    assert not EffectSet(now_fn=Relogio()).active("shield")


def test_duracao_empilha_pelo_maior_fim_nao_soma():
    r = Relogio()
    e = EffectSet(now_fn=r)
    e.activate("shield", 5.0)
    r.avanca(1.0)
    e.activate("shield", 5.0)  # termina em 6.0, nao em 7.0
    r.avanca(5.5)
    assert not e.active("shield")
    r.avanca(0.6)
    assert not e.active("shield")


def test_reativar_estende_se_o_novo_fim_for_maior():
    r = Relogio()
    e = EffectSet(now_fn=r)
    e.activate("shield", 1.0)
    e.activate("shield", 10.0)
    r.avanca(5.0)
    assert e.active("shield")


def test_remaining_diminui_com_o_tempo():
    r = Relogio()
    e = EffectSet(now_fn=r)
    e.activate("rage", 10.0)
    r.avanca(4.0)
    assert 5.9 < e.remaining("rage") < 6.1


def test_expire_remove_efeitos_vencidos():
    r = Relogio()
    e = EffectSet(now_fn=r)
    e.activate("jump", 1.0)
    r.avanca(2.0)
    e.expire()
    assert e.remaining("jump") == 0.0


def test_anuncio_fica_ativo_ate_o_ttl():
    r = Relogio()
    q = AnnouncementQueue(now_fn=r)
    q.push(kind="gift", actor="Joao", text="mandou Rose", detail="+5 XP", ttl=4.0)
    assert len(q.active()) == 1
    r.avanca(4.1)
    assert q.active() == []


def test_anuncio_expira_sozinho_sem_chamada_explicita():
    r = Relogio()
    q = AnnouncementQueue(now_fn=r)
    q.push(kind="gift", actor="Joao", text="mandou Rose", ttl=1.0)
    r.avanca(5.0)
    q.push(kind="gift", actor="Maria", text="mandou GG", ttl=1.0)
    assert [a.actor for a in q.active()] == ["Maria"]


def test_fila_de_anuncios_respeita_o_tamanho_maximo():
    q = AnnouncementQueue(now_fn=Relogio(), max_size=3)
    for i in range(10):
        q.push(kind="gift", actor=f"u{i}", text="x", ttl=100.0)
    assert len(q.active()) == 3


def test_fila_de_anuncios_mantem_os_mais_recentes():
    q = AnnouncementQueue(now_fn=Relogio(), max_size=2)
    for nome in ("a", "b", "c", "d"):
        q.push(kind="gift", actor=nome, text="x", ttl=100.0)
    assert [a.actor for a in q.active()] == ["c", "d"]


def test_anuncio_big_e_marcado():
    q = AnnouncementQueue(now_fn=Relogio())
    q.push(kind="levelup", actor="", text="LEVEL UP!", big=True, ttl=3.0)
    assert q.active()[0].big is True
```

- [ ] **Step 2: Rodar e ver falhar**

Run: `pytest tests/test_effects.py -v`
Esperado: FAIL — `ModuleNotFoundError: No module named 'game.effects'`

- [ ] **Step 3: Implementar**

```python
import time
from dataclasses import dataclass, field
from typing import Callable


@dataclass
class Announcement:
    """Um aviso para a tela: presente, follow, level up, evento especial."""

    kind: str
    actor: str
    text: str
    detail: str = ""
    icon: str = ""
    big: bool = False
    ttl: float = 4.0
    created: float = 0.0
    birth: float = 0.0

    def age(self, now: float) -> float:
        return now - self.created

    def alpha(self, now: float) -> float:
        """Desaparece suavemente no ultimo 0,6s de vida."""
        if self.ttl <= 0:
            return 0.0
        restante = self.ttl - self.age(now)
        if restante <= 0:
            return 0.0
        if restante >= 0.6:
            return 1.0
        return restante / 0.6


class EffectSet:
    """Efeitos temporarios com prazo de validade.

    Reativar um efeito pega o MAIOR fim, nao soma as duracoes: dois
    escudos de 5s dao 5s, nao 10s.
    """

    def __init__(self, now_fn: Callable[[], float] = time.monotonic):
        self._now = now_fn
        self._fins: dict[str, float] = {}

    def activate(self, name: str, duration: float) -> None:
        if duration <= 0:
            return
        fim = self._now() + duration
        self._fins[name] = max(self._fins.get(name, 0.0), fim)

    def active(self, name: str) -> bool:
        return self._fins.get(name, 0.0) > self._now()

    def remaining(self, name: str) -> float:
        return max(0.0, self._fins.get(name, 0.0) - self._now())

    def expire(self) -> None:
        agora = self._now()
        self._fins = {k: v for k, v in self._fins.items() if v > agora}

    def active_names(self) -> list[str]:
        agora = self._now()
        return [k for k, v in self._fins.items() if v > agora]


class AnnouncementQueue:
    """Fila de avisos exibidos na tela.

    Pertence ao jogo, nao ao renderer: qualquer renderer futuro mostra os
    mesmos avisos lendo este estado.
    """

    def __init__(
        self,
        now_fn: Callable[[], float] = time.monotonic,
        max_size: int = 8,
    ):
        self._now = now_fn
        self._max = max(1, max_size)
        self._itens: list[Announcement] = []

    def push(
        self,
        kind: str,
        actor: str,
        text: str,
        detail: str = "",
        icon: str = "",
        ttl: float = 4.0,
        big: bool = False,
    ) -> Announcement:
        agora = self._now()
        item = Announcement(
            kind=kind,
            actor=actor,
            text=text,
            detail=detail,
            icon=icon,
            big=big,
            ttl=ttl,
            created=agora,
            birth=agora,
        )
        self._itens.append(item)
        self._expirar(agora)
        # Corta os mais antigos, mantendo os mais recentes.
        if len(self._itens) > self._max:
            self._itens = self._itens[-self._max :]
        return item

    def _expirar(self, agora: float) -> None:
        self._itens = [a for a in self._itens if a.age(agora) < a.ttl]

    def active(self) -> list[Announcement]:
        self._expirar(self._now())
        return list(self._itens)

    def expire(self) -> None:
        self._expirar(self._now())
```

- [ ] **Step 4: Rodar e ver passar**

Run: `pytest tests/test_effects.py -v`
Esperado: 12 passed

- [ ] **Step 5: Commitar**

```bash
git add game/effects.py tests/test_effects.py
git commit -m "Adiciona efeitos temporarios e fila de anuncios"
```

---

### Task 8: `game/engine.py` + `game/actions.py` — XP, level e registro de ações

**Files:**
- Create: `game/actions.py`
- Modify: `game/engine.py` (reescrita completa)
- Modify: `core/config.py` (trocar `ACOES_VALIDAS` local pelo import)
- Test: `tests/test_levels.py`, `tests/test_actions.py`

**Interfaces:**
- Consumes: `game.state.GameState`, `game.entities.{Character,Enemy,Boss}`, `game.effects.{EffectSet,AnnouncementQueue}`, `core.events.LiveEvent`, `core.ratelimit.RateLimiter`
- Produces: `GameEngine(config, now_fn=time.monotonic)` com `state`, `apply_action(action, payload, event)`, `update(dt)`, `add_xp(amount)`, `damage(amount)`, `spawn_enemy(count)`, `spawn_boss()`, `steer(direction)`, `xp_para_subir(level) -> int`; `ACTION_REGISTRY: dict[str, Callable]`, `register(name)` (decorator), `known_actions() -> frozenset[str]`

**Contexto:** esta tarefa entrega XP/level, o registro de ações e a quarta camada de anti-spam (teto de entidades). O movimento por intenção e a simulação de inimigos ficam para a Task 9.

- [ ] **Step 1: Escrever `tests/test_levels.py`**

```python
from game.engine import GameEngine

CONFIG = {
    "game": {
        "max_hp": 100,
        "initial_hp": 100,
        "initial_xp": 0,
        "initial_level": 1,
        "initial_speed": 220,
        "xp_per_level": 100,
        "xp_level_step": 25,
        "base_enemy_damage": 5,
    },
    "limits": {"max_enemies": 40},
}


def test_curva_de_xp_cresce_por_nivel():
    e = GameEngine(CONFIG)
    assert e.xp_para_subir(1) == 100
    assert e.xp_para_subir(2) == 125
    assert e.xp_para_subir(3) == 150


def test_xp_insuficiente_nao_sobe_de_nivel():
    e = GameEngine(CONFIG)
    e.add_xp(99)
    assert e.state.level == 1
    assert e.state.xp == 99


def test_xp_exato_sobe_de_nivel():
    e = GameEngine(CONFIG)
    e.add_xp(100)
    assert e.state.level == 2
    assert e.state.xp == 0


def test_xp_restante_e_carregado_para_o_proximo_nivel():
    e = GameEngine(CONFIG)
    e.add_xp(120)
    assert e.state.level == 2
    assert e.state.xp == 20


def test_um_presente_grande_sobe_varios_niveis():
    e = GameEngine(CONFIG)
    e.add_xp(100 + 125 + 150 + 10)
    assert e.state.level == 4
    assert e.state.xp == 10


def test_subir_de_nivel_aumenta_max_hp_e_cura():
    e = GameEngine(CONFIG)
    e.damage(50)
    e.add_xp(100)
    assert e.state.max_hp > 100
    assert e.state.hp == e.state.max_hp


def test_subir_de_nivel_empurra_anuncio():
    e = GameEngine(CONFIG)
    e.add_xp(100)
    kinds = [a.kind for a in e.state.announcements.active()]
    assert "levelup" in kinds
    assert any(a.big for a in e.state.announcements.active() if a.kind == "levelup")


def test_xp_zero_ou_negativo_nao_faz_nada():
    e = GameEngine(CONFIG)
    e.add_xp(0)
    e.add_xp(-50)
    assert e.state.xp == 0
    assert e.state.level == 1


def test_dano_reduz_hp():
    e = GameEngine(CONFIG)
    e.damage(30)
    assert e.state.hp == 70


def test_hp_nunca_fica_negativo():
    e = GameEngine(CONFIG)
    e.damage(9999)
    assert e.state.hp >= 0
```

- [ ] **Step 2: Escrever `tests/test_actions.py`**

```python
import pytest

from core.events import EventType, LiveEvent
from game.actions import known_actions
from game.engine import GameEngine

CONFIG = {
    "game": {
        "max_hp": 100,
        "initial_hp": 100,
        "initial_speed": 220,
        "xp_per_level": 100,
        "xp_level_step": 25,
        "base_enemy_damage": 5,
    },
    "limits": {"max_enemies": 5},
}


def _evento(tipo=EventType.GIFT, **kw):
    return LiveEvent(type=tipo, username="joao", **kw)


def test_todas_as_acoes_do_contrato_existem():
    esperadas = {
        "xp", "heal", "damage", "run", "jump", "speed",
        "shield", "rage", "spawn_enemy", "special", "boss", "mega",
    }
    assert esperadas <= known_actions()


def test_acao_xp():
    e = GameEngine(CONFIG)
    e.apply_action("xp", {"xp": 40}, _evento())
    assert e.state.xp == 40


def test_acao_heal_nao_passa_do_maximo():
    e = GameEngine(CONFIG)
    e.damage(50)
    e.apply_action("heal", {"amount": 999}, _evento())
    assert e.state.hp == e.state.max_hp


def test_acao_damage():
    e = GameEngine(CONFIG)
    e.apply_action("damage", {"amount": 25}, _evento())
    assert e.state.hp == 75


def test_acao_shield_bloqueia_dano():
    e = GameEngine(CONFIG)
    e.apply_action("shield", {"duration": 5}, _evento())
    e.damage(30)
    assert e.state.hp == 100


def test_acao_spawn_enemy_cria_inimigos():
    e = GameEngine(CONFIG)
    e.apply_action("spawn_enemy", {"amount": 3}, _evento())
    assert len(e.state.enemies) == 3


def test_spawn_enemy_respeita_o_teto_de_entidades():
    e = GameEngine(CONFIG)  # max_enemies = 5
    e.apply_action("spawn_enemy", {"amount": 500}, _evento())
    assert len(e.state.enemies) == 5


def test_teto_de_entidades_vale_entre_chamadas():
    e = GameEngine(CONFIG)
    for _ in range(20):
        e.apply_action("spawn_enemy", {"amount": 2}, _evento())
    assert len(e.state.enemies) <= 5


def test_acao_boss_cria_um_boss():
    e = GameEngine(CONFIG)
    e.apply_action("boss", {}, _evento())
    assert e.state.boss is not None
    assert e.state.boss.hp > 0


def test_boss_nao_duplica_se_um_ja_existe():
    e = GameEngine(CONFIG)
    e.apply_action("boss", {}, _evento())
    primeiro = e.state.boss
    e.apply_action("boss", {}, _evento())
    assert e.state.boss is primeiro


def test_acao_mega_empurra_anuncio_grande():
    e = GameEngine(CONFIG)
    e.apply_action("mega", {"duration": 8}, _evento())
    assert any(a.big for a in e.state.announcements.active())


def test_acao_especial_empurra_anuncio():
    e = GameEngine(CONFIG)
    e.apply_action("special", {"duration": 5}, _evento())
    assert any(a.kind == "special" for a in e.state.announcements.active())


def test_acao_desconhecida_nao_levanta_excecao():
    e = GameEngine(CONFIG)
    e.apply_action("nao_existe", {}, _evento())  # nao pode quebrar o loop


def test_contadores_por_tipo_de_evento():
    e = GameEngine(CONFIG)
    e.apply_action("xp", {"xp": 1}, _evento(EventType.GIFT, quantity=3))
    e.apply_action("xp", {"xp": 1}, _evento(EventType.FOLLOW))
    e.apply_action("xp", {"xp": 1}, _evento(EventType.SHARE))
    e.apply_action("xp", {"xp": 1}, _evento(EventType.LIKE, like_delta=7))
    assert e.state.total_gifts == 3
    assert e.state.total_followers == 1
    assert e.state.total_shares == 1
    assert e.state.total_likes == 7
```

- [ ] **Step 3: Rodar e ver falhar**

Run: `pytest tests/test_levels.py tests/test_actions.py -v`
Esperado: FAIL — `ModuleNotFoundError: No module named 'game.actions'`

- [ ] **Step 4: Implementar `game/actions.py`**

```python
from typing import TYPE_CHECKING, Callable

if TYPE_CHECKING:  # evita import circular em tempo de execucao
    from core.events import LiveEvent
    from game.engine import GameEngine

ActionHandler = Callable[["GameEngine", dict, "LiveEvent"], None]

ACTION_REGISTRY: dict[str, ActionHandler] = {}


def register(name: str) -> Callable[[ActionHandler], ActionHandler]:
    """Decorator: torna uma funcao uma acao configuravel no config.json."""

    def deco(fn: ActionHandler) -> ActionHandler:
        ACTION_REGISTRY[name] = fn
        return fn

    return deco


def known_actions() -> frozenset[str]:
    return frozenset(ACTION_REGISTRY)
```

> As funções de ação são registradas no fim de `game/engine.py`, onde têm acesso ao `GameEngine`. `game/actions.py` guarda só o registro, para que `core/config.py` possa importar `known_actions()` sem importar o engine — o que criaria um ciclo.

- [ ] **Step 5: Implementar `game/engine.py`**

```python
import logging
import random
import time
from typing import Callable

from core.events import EventType, LiveEvent
from game.actions import ACTION_REGISTRY, register
from game.effects import AnnouncementQueue, EffectSet
from game.entities import Boss, Enemy
from game.state import GameState

logger = logging.getLogger(__name__)

ANUNCIO_TTL = 4.0


class GameEngine:
    """Regras do jogo, sem qualquer dependencia do Pygame.

    Esta e a parte que sobrevive se a renderizacao for trocada por
    navegador, Unity ou Godot.
    """

    def __init__(self, config: dict, now_fn: Callable[[], float] = time.monotonic):
        cfg = config["game"]
        limites = config.get("limits", {})

        self._now = now_fn
        self.xp_per_level = int(cfg.get("xp_per_level", 100))
        self.xp_level_step = int(cfg.get("xp_level_step", 25))
        self.base_enemy_damage = int(cfg.get("base_enemy_damage", 5))
        self.max_enemies = int(limites.get("max_enemies", 40))
        self.intent_half_life = float(cfg.get("intent_half_life", 1.5))
        self.intent_accel = float(cfg.get("intent_accel", 1800.0))
        self.intent_max_speed = float(cfg.get("intent_max_speed", 420.0))
        self.intent_friction = float(cfg.get("intent_friction", 6.0))

        estado = GameState(
            hp=int(cfg.get("initial_hp", 100)),
            max_hp=int(cfg.get("max_hp", 100)),
            xp=int(cfg.get("initial_xp", 0)),
            level=int(cfg.get("initial_level", 1)),
            speed=float(cfg.get("initial_speed", 220)),
            base_speed=float(cfg.get("initial_speed", 220)),
        )
        estado.effects = EffectSet(now_fn=now_fn)
        estado.announcements = AnnouncementQueue(
            now_fn=now_fn, max_size=int(config.get("app", {}).get("feed_size", 6)) + 2
        )
        self.state = estado

        # Intencao de direcao vinda dos comentarios (Task 9).
        self._intent = 0.0
        self._intent_until = 0.0

    # ---------- experiencia ----------

    def xp_para_subir(self, level: int) -> int:
        """Custo crescente: 100, 125, 150, ..."""
        return self.xp_per_level + (level - 1) * self.xp_level_step

    def add_xp(self, amount: int) -> None:
        if amount <= 0:
            return
        self.state.xp += amount
        while self.state.xp >= self.xp_para_subir(self.state.level):
            self.state.xp -= self.xp_para_subir(self.state.level)
            self.state.level += 1
            self.state.max_hp += 10
            self.state.hp = self.state.max_hp
            self.state.base_speed += 5
            self.state.speed = self.state.base_speed
            self.state.announcements.push(
                kind="levelup",
                actor="",
                text="LEVEL UP!",
                detail=f"Nivel {self.state.level}",
                icon="*",
                ttl=3.0,
                big=True,
            )
            logger.info("LEVEL UP | nivel=%s", self.state.level)

    # ---------- dano e cura ----------

    def heal(self, amount: int) -> int:
        antes = self.state.hp
        self.state.hp = min(self.state.max_hp, self.state.hp + max(0, amount))
        return self.state.hp - antes

    def damage(self, amount: int) -> None:
        if self.state.effects.active("shield"):
            self.state.effects.activate("shield_hit", 0.3)
            return
        if self.state.effects.active("mega"):
            return  # mega evento torna o personagem invulneravel
        self.state.hp = max(0, self.state.hp - max(0, amount))
        if self.state.hp == 0:
            self._respawn()

    def _respawn(self) -> None:
        self.state.hp = self.state.max_hp
        self.state.xp = max(0, self.state.xp - 25)
        self.state.enemies.clear()
        self.state.boss = None
        self.state.announcements.push(
            kind="system", actor="", text="O personagem caiu!", detail="Renascendo", ttl=3.0, big=True
        )

    # ---------- entidades ----------

    def spawn_enemy(self, count: int) -> int:
        """Cria inimigos ate o teto. Retorna quantos foram criados."""
        espaco = self.max_enemies - len(self.state.enemies)
        criar = max(0, min(count, espaco))
        for _ in range(criar):
            self.state.enemies.append(
                Enemy(
                    x=random.uniform(80.0, 1000.0),
                    y=random.uniform(-120.0, 120.0),
                )
            )
        return criar

    def spawn_boss(self) -> Boss:
        if self.state.boss is not None and self.state.boss.is_alive():
            return self.state.boss
        hp = 300 + self.state.level * 50
        boss = Boss(x=540.0, y=200.0, hp=hp, max_hp=hp)
        self.state.boss = boss
        self.state.announcements.push(
            kind="boss", actor="", text="CHEFÃO!", detail="Derrote para ganhar XP", ttl=5.0, big=True
        )
        return boss

    # ---------- intencao de direcao (Task 9 completa o movimento) ----------

    def steer(self, direction: float) -> None:
        """Comentario de direcao. `direction` em [-1, +1]."""
        d = max(-1.0, min(1.0, float(direction)))
        self._intent = max(-3.0, min(3.0, self._intent + d))
        self._intent_until = self._now() + self.intent_half_life

    def intent(self) -> float:
        return self._intent

    # ---------- ciclo ----------

    def update(self, dt: float) -> None:
        self.state.effects.expire()
        self.state.announcements.expire()

    # ---------- despacho ----------

    def apply_action(self, action: str, payload: dict, event: LiveEvent) -> None:
        try:
            self._contabilizar(event)
            handler = ACTION_REGISTRY.get(action)
            if handler is None:
                logger.warning("Acao desconhecida: %s", action)
                return
            handler(self, payload, event)
        except Exception:
            # Uma acao com defeito nao pode derrubar o loop do jogo.
            logger.exception("Erro aplicando acao %s", action)

    def _contabilizar(self, event: LiveEvent) -> None:
        if event.type == EventType.GIFT:
            self.state.total_gifts += max(1, event.quantity)
        elif event.type == EventType.FOLLOW:
            self.state.total_followers += 1
        elif event.type == EventType.SHARE:
            self.state.total_shares += 1
        elif event.type == EventType.LIKE:
            self.state.total_likes += max(1, event.like_delta or 1)


# ---------------------------------------------------------------------------
# Acoes. Cada uma vira um nome valido em config.json.
# ---------------------------------------------------------------------------


def _anunciar(engine: GameEngine, event: LiveEvent, texto: str, detalhe: str = "") -> None:
    if not event.actor() or event.actor() == "desconhecido":
        return
    engine.state.announcements.push(
        kind=str(event.type), actor=event.actor(), text=texto, detail=detalhe, ttl=ANUNCIO_TTL
    )


@register("xp")
def _acao_xp(engine: GameEngine, payload: dict, event: LiveEvent) -> None:
    valor = int(payload.get("xp", 0))
    engine.add_xp(valor)
    _anunciar(engine, event, "ganhou XP", f"+{valor} XP")


@register("heal")
def _acao_heal(engine: GameEngine, payload: dict, event: LiveEvent) -> None:
    curado = engine.heal(int(payload.get("amount", 10)))
    _anunciar(engine, event, "curou o personagem", f"+{curado} HP")


@register("damage")
def _acao_damage(engine: GameEngine, payload: dict, event: LiveEvent) -> None:
    valor = int(payload.get("amount", 5))
    engine.damage(valor)
    _anunciar(engine, event, "causou dano", f"-{valor} HP")


@register("run")
def _acao_run(engine: GameEngine, payload: dict, event: LiveEvent) -> None:
    engine.state.effects.activate("run", float(payload.get("duration", 3)))
    _anunciar(engine, event, "fez o personagem CORRER")


@register("jump")
def _acao_jump(engine: GameEngine, payload: dict, event: LiveEvent) -> None:
    engine.state.effects.activate("jump", float(payload.get("duration", 0.8)))
    _anunciar(engine, event, "fez o personagem PULAR")


@register("speed")
def _acao_speed(engine: GameEngine, payload: dict, event: LiveEvent) -> None:
    ganho = float(payload.get("amount", 60))
    engine.state.speed = engine.state.base_speed + ganho
    engine.state.effects.activate("speed", float(payload.get("duration", 5)))
    _anunciar(engine, event, "acelerou", f"+{ganho:.0f}")


@register("shield")
def _acao_shield(engine: GameEngine, payload: dict, event: LiveEvent) -> None:
    engine.state.effects.activate("shield", float(payload.get("duration", 5)))
    _anunciar(engine, event, "ativou ESCUDO")


@register("rage")
def _acao_rage(engine: GameEngine, payload: dict, event: LiveEvent) -> None:
    engine.state.effects.activate("rage", float(payload.get("duration", 8)))
    _anunciar(engine, event, "ativou FÚRIA")


@register("spawn_enemy")
def _acao_spawn_enemy(engine: GameEngine, payload: dict, event: LiveEvent) -> None:
    criados = engine.spawn_enemy(int(payload.get("amount", 1)))
    if criados:
        _anunciar(engine, event, "invocou inimigos", f"+{criados}")


@register("special")
def _acao_special(engine: GameEngine, payload: dict, event: LiveEvent) -> None:
    engine.state.effects.activate("special", float(payload.get("duration", 5)))
    engine.state.announcements.push(
        kind="special",
        actor=event.actor(),
        text="EVENTO ESPECIAL",
        detail=f"{event.actor()} ativou!",
        ttl=5.0,
        big=True,
    )


@register("boss")
def _acao_boss(engine: GameEngine, payload: dict, event: LiveEvent) -> None:
    engine.spawn_boss()


@register("mega")
def _acao_mega(engine: GameEngine, payload: dict, event: LiveEvent) -> None:
    duracao = float(payload.get("duration", 10))
    engine.state.effects.activate("mega", duracao)
    engine.state.effects.activate("shield", duracao)
    engine.add_xp(int(payload.get("xp", 100)))
    engine.state.announcements.push(
        kind="mega",
        actor=event.actor(),
        text="MEGA EVENTO",
        detail=f"{event.actor()} ativou!",
        ttl=6.0,
        big=True,
    )
```

- [ ] **Step 6: Trocar `ACOES_VALIDAS` por import em `core/config.py`**

Substituir o bloco:

```python
ACOES_VALIDAS = frozenset({
    "xp", "heal", "damage", "run", "jump", "speed",
    "shield", "rage", "spawn_enemy", "special", "boss", "mega",
})
```

por:

```python
from game.actions import known_actions

ACOES_VALIDAS = known_actions()
```

> Isso é seguro: `game/actions.py` só tem o registro e não importa `game/engine.py`, então não há ciclo.

- [ ] **Step 7: Rodar tudo e ver passar**

Run: `pytest -v`
Esperado: todos passam. `test_config.py::test_acao_desconhecida_e_recusada_com_nome_do_presente` continua passando, agora validando contra o registro real.

- [ ] **Step 8: Commitar**

```bash
git add game/engine.py game/actions.py core/config.py tests/test_levels.py tests/test_actions.py
git commit -m "Reescreve o motor com registro de acoes, curva de XP e teto de entidades"
```

---

### Task 9: Movimento por intenção e simulação

**Files:**
- Modify: `game/engine.py` (`update`, `steer`, `intent`; adicionar `_mover`, `_mover_inimigos`)
- Test: `tests/test_intent.py`

**Interfaces:**
- Consumes: `GameEngine` da Task 8
- Produces: `GameEngine.update(dt)` que move o personagem por intenção, faz inimigos descerem, aplica dano de contato e resolve o boss

**Contexto:** o espectador comanda em `T` e vê em `T+15s` (§12.7 da spec). Por isso a intenção decai devagar e o personagem **acelera** em vez de teleportar. Intenções opostas se cancelam.

- [ ] **Step 1: Escrever o teste que falha**

```python
from core.events import EventType, LiveEvent
from game.engine import GameEngine
from game.entities import Enemy

CONFIG = {
    "game": {
        "max_hp": 100,
        "initial_hp": 100,
        "initial_speed": 220,
        "xp_per_level": 100,
        "xp_level_step": 25,
        "base_enemy_damage": 5,
        "intent_half_life": 1.5,
        "intent_accel": 1800.0,
        "intent_max_speed": 420.0,
        "intent_friction": 6.0,
    },
    "limits": {"max_enemies": 10},
}


class Relogio:
    def __init__(self):
        self.t = 0.0

    def __call__(self) -> float:
        return self.t

    def avanca(self, dt: float) -> None:
        self.t += dt


def _engine(relogio=None):
    return GameEngine(CONFIG, now_fn=relogio or Relogio())


def test_sem_comando_o_personagem_nao_dispara():
    e = _engine()
    x0 = e.state.character.x
    for _ in range(10):
        e.update(1 / 60)
    assert abs(e.state.character.x - x0) < 1.0


def test_comando_move_o_personagem_para_a_direita():
    e = _engine()
    x0 = e.state.character.x
    e.steer(+1)
    for _ in range(60):
        e.update(1 / 60)
    assert e.state.character.x > x0


def test_comando_move_para_a_esquerda():
    e = _engine()
    x0 = e.state.character.x
    e.steer(-1)
    for _ in range(60):
        e.update(1 / 60)
    assert e.state.character.x < x0


def test_personagem_acelera_em_vez_de_teleportar():
    e = _engine()
    x0 = e.state.character.x
    e.steer(+1)
    e.update(1 / 60)
    # Um unico frame nao pode jogar o personagem do outro lado da tela.
    assert e.state.character.x - x0 < 30.0


def test_intencoes_opostas_se_cancelam():
    e = _engine()
    e.steer(+1)
    e.steer(-1)
    assert abs(e.intent()) < 0.5


def test_intencao_decai_com_o_tempo():
    relogio = Relogio()
    e = _engine(relogio)
    e.steer(+1)
    forte = abs(e.intent())
    relogio.avanca(3.0)
    for _ in range(10):
        e.update(1 / 60)
    assert abs(e.intent()) < forte


def test_intencao_nao_explode_com_spam_de_comentarios():
    e = _engine()
    for _ in range(500):
        e.steer(+1)
    assert abs(e.intent()) <= 3.0


def test_personagem_nao_sai_da_tela():
    e = _engine()
    e.steer(+1)
    for _ in range(600):
        e.update(1 / 60)
    assert e.state.character.x <= 1080
    e.steer(-1)
    for _ in range(600):
        e.update(1 / 60)
    assert e.state.character.x >= 0


def test_inimigo_desce_em_direcao_ao_personagem():
    e = _engine()
    e.state.enemies.append(Enemy(x=540.0, y=100.0))
    y0 = e.state.enemies[0].y
    e.update(1 / 60)
    assert e.state.enemies[0].y > y0


def test_inimigo_que_alcanca_causa_dano_e_some():
    e = _engine()
    alvo = e.state.character
    e.state.enemies.append(Enemy(x=alvo.x, y=alvo.y + 10.0))
    e.update(1 / 60)
    assert e.state.hp < 100
    assert len(e.state.enemies) == 0


def test_escudo_bloqueia_dano_de_contato():
    e = _engine()
    e.apply_action("shield", {"duration": 5}, LiveEvent(type=EventType.GIFT))
    alvo = e.state.character
    e.state.enemies.append(Enemy(x=alvo.x, y=alvo.y + 10.0))
    e.update(1 / 60)
    assert e.state.hp == 100


def test_pulo_afeta_o_y_offset_e_volta_ao_chao():
    relogio = Relogio()
    e = _engine(relogio)
    e.apply_action("jump", {"duration": 0.8}, LiveEvent(type=EventType.GIFT))
    for _ in range(10):
        e.update(1 / 60)
    assert e.state.character.y_offset > 0
    relogio.avanca(2.0)
    e.update(1 / 60)
    assert e.state.character.y_offset == 0.0


def test_boss_recebe_dano_e_morre():
    e = _engine()
    boss = e.spawn_boss()
    boss.hp = 1
    e.apply_action("damage", {"amount": 50}, LiveEvent(type=EventType.GIFT))
    e.update(1 / 60)
    assert e.state.boss is None or not e.state.boss.is_alive()


def test_update_com_dt_grande_nao_quebra():
    e = _engine()
    e.steer(+1)
    e.update(5.0)  # uma pausa longa nao pode explodir a simulacao
    assert 0 <= e.state.character.x <= 1080
```

- [ ] **Step 2: Rodar e ver falhar**

Run: `pytest tests/test_intent.py -v`
Esperado: FAIL — o personagem não se move (`assert x > x0` falha)

- [ ] **Step 3: Implementar**

Substituir `steer`, `intent` e `update` em `game/engine.py`, e adicionar os métodos privados:

```python
    def steer(self, direction: float) -> None:
        """Comentario de direcao. `direction` em [-1, +1].

        A soma e limitada: 500 pessoas gritando 'direita' nao podem virar
        um vetor absurdo.
        """
        d = max(-1.0, min(1.0, float(direction)))
        self._intent = max(-3.0, min(3.0, self._intent + d))
        self._intent_until = self._now() + self.intent_half_life

    def intent(self) -> float:
        return self._intent

    def _decair_intencao(self, dt: float) -> None:
        if dt <= 0:
            return
        if self._now() >= self._intent_until:
            # Sem comando recente: decai ate zero.
            fator = 0.5 ** (dt / max(0.01, self.intent_half_life))
            self._intent *= fator
            if abs(self._intent) < 0.01:
                self._intent = 0.0

    def _mover_personagem(self, dt: float) -> None:
        """Acelera na direcao da intencao, em vez de teleportar."""
        personagem = self.state.character
        alvo = self._intent * self.intent_max_speed
        diferenca = alvo - personagem.vx
        passo = self.intent_accel * dt
        personagem.vx += max(-passo, min(passo, diferenca))
        personagem.vx -= personagem.vx * min(1.0, self.intent_friction * dt)

        if abs(personagem.vx) < 1.0:
            personagem.vx = 0.0
            return

        personagem.x += personagem.vx * dt
        personagem.facing = 1 if personagem.vx >= 0 else -1

        margem = personagem.radius
        largura = self.largura
        if personagem.x < margem:
            personagem.x = margem
            personagem.vx = 0.0
        elif personagem.x > largura - margem:
            personagem.x = largura - margem
            personagem.vx = 0.0

    def _animar_pulo(self) -> None:
        if not self.state.effects.active("jump"):
            self.state.character.y_offset = 0.0
            return
        restante = self.state.effects.remaining("jump")
        duracao = max(0.05, self._jump_duration)
        fase = 1.0 - (restante / duracao)
        self.state.character.y_offset = abs(math.sin(fase * math.pi)) * 150.0

    def _mover_inimigos(self, dt: float) -> None:
        alvo = self.state.character
        vivos: list[Enemy] = []
        for inimigo in self.state.enemies:
            dx = alvo.x - inimigo.x
            dy = alvo.y - inimigo.y
            dist = math.hypot(dx, dy) or 1.0
            inimigo.x += (dx / dist) * inimigo.speed * dt
            inimigo.y += (dy / dist) * inimigo.speed * dt
            if inimigo.reached(alvo.x, alvo.y, raio=alvo.radius + 14.0):
                self.damage(self.base_enemy_damage)
                continue
            vivos.append(inimigo)
        self.state.enemies = vivos[: self.max_enemies]

    def _atualizar_boss(self, dt: float) -> None:
        boss = self.state.boss
        if boss is None:
            return
        if not boss.is_alive():
            self.add_xp(80 + self.state.level * 20)
            self.state.announcements.push(
                kind="boss", actor="", text="CHEFÃO DERROTADO", detail="+XP", ttl=4.0, big=True
            )
            self.state.boss = None
            return

        alvo = self.state.character
        dx = alvo.x - boss.x
        dy = alvo.y - boss.y
        dist = math.hypot(dx, dy) or 1.0
        boss.x += (dx / dist) * boss.speed * dt
        boss.y += (dy / dist) * boss.speed * dt

        boss.since_summon += dt
        if boss.since_summon >= boss.summon_every:
            boss.since_summon = 0.0
            self.spawn_enemy(2)

        if boss.reached(alvo.x, alvo.y, raio=alvo.radius + boss.radius):
            self.damage(self.base_enemy_damage * 2)

    def update(self, dt: float) -> None:
        # Uma pausa longa (janela arrastada, GC) nao pode teleportar nada:
        # o passo e limitado antes de simular.
        dt = max(0.0, min(dt, 0.05))

        self._decair_intencao(dt)
        self._mover_personagem(dt)
        self._animar_pulo()
        self._mover_inimigos(dt)
        self._atualizar_boss(dt)
        self.state.effects.expire()
        self.state.announcements.expire()
```

E adicionar em `__init__`, junto das outras configs:

```python
        self.largura = float(config["app"].get("window_width", 1080))
        self._jump_duration = 0.8
```

E o import de `math` no topo:

```python
import math
```

E em `_acao_jump`, guardar a duração para a animação:

```python
@register("jump")
def _acao_jump(engine: GameEngine, payload: dict, event: LiveEvent) -> None:
    duracao = float(payload.get("duration", 0.8))
    engine._jump_duration = duracao
    engine.state.effects.activate("jump", duracao)
    _anunciar(engine, event, "fez o personagem PULAR")
```

- [ ] **Step 4: Rodar e ver passar**

Run: `pytest tests/test_intent.py -v`
Esperado: 15 passed

- [ ] **Step 5: Rodar a suíte inteira**

Run: `pytest -v`
Esperado: tudo passa

- [ ] **Step 6: Commitar**

```bash
git add game/engine.py tests/test_intent.py
git commit -m "Adiciona movimento por vetor de intencao e simulacao de inimigos"
```

---

### Task 10: `core/rules.py` — motor de regras

**Files:**
- Modify: `core/rules.py` (reescrita)
- Test: `tests/test_rules.py`

**Interfaces:**
- Consumes: `core.events.LiveEvent`, `core.ratelimit.RateLimiter`, `GameEngine.apply_action`, `core.config.normalize`
- Produces: `normalize(text) -> str`; `RuleEngine(config, game, limiter, on_event=None)` com `process(event)`

**Contexto:** casa com o §6 da spec. O bug a corrigir: o laço de milestones chama `_run_action`, que aplica o cooldown da regra — com `cooldown > 0`, o segundo milestone da mesma rajada era descartado em silêncio.

- [ ] **Step 1: Escrever o teste que falha**

```python
import pytest

from core.events import EventType, LiveEvent
from core.ratelimit import RateLimiter
from core.rules import RuleEngine, normalize
from game.engine import GameEngine


class Relogio:
    def __init__(self):
        self.t = 0.0

    def __call__(self) -> float:
        return self.t

    def avanca(self, dt: float) -> None:
        self.t += dt


def _config(regras: dict) -> dict:
    base = {"gifts": [], "comments": [], "likes": [], "follows": [], "shares": []}
    base.update(regras)
    return {
        "app": {"window_width": 1080, "feed_size": 6},
        "game": {
            "max_hp": 100, "initial_hp": 100, "initial_speed": 220,
            "xp_per_level": 100, "xp_level_step": 25, "base_enemy_damage": 5,
        },
        "limits": {"max_enemies": 10, "action_budget": {"spawn_enemy": 2.0}},
        "rules": base,
    }


def _montar(regras: dict, relogio=None):
    relogio = relogio or Relogio()
    cfg = _config(regras)
    game = GameEngine(cfg, now_fn=relogio)
    limiter = RateLimiter(action_budget=cfg["limits"]["action_budget"], now_fn=relogio)
    return RuleEngine(cfg, game, limiter), game, relogio


def test_normalize_remove_acento_e_caixa():
    assert normalize("CORREÇÃO") == "correcao"
    assert normalize("  Corre  ") == "corre"


def test_comentario_dispara_acao():
    engine, game, _ = _montar({"comments": [{"contains": "corre", "action": "run", "duration": 3}]})
    engine.process(LiveEvent(type=EventType.COMMENT, username="maria", text="corre"))
    assert game.state.effects.active("run")


def test_comentario_com_emoji_e_caixa_ainda_casa():
    engine, game, _ = _montar({"comments": [{"contains": "corre", "action": "run", "duration": 3}]})
    engine.process(LiveEvent(type=EventType.COMMENT, username="m", text="CORRE!!! 🏃"))
    assert game.state.effects.active("run")


def test_comentario_acentuado_casa_regra_sem_acento():
    engine, game, _ = _montar({"comments": [{"contains": "corre", "action": "run", "duration": 3}]})
    engine.process(LiveEvent(type=EventType.COMMENT, username="m", text="corré"))
    assert game.state.effects.active("run")


def test_comentario_sem_regra_nao_faz_nada():
    engine, game, _ = _montar({"comments": []})
    engine.process(LiveEvent(type=EventType.COMMENT, username="m", text="oi"))
    assert game.state.xp == 0


def test_comentario_de_direita_empurra_a_intencao():
    engine, game, _ = _montar({"comments": [{"contains": "direita", "action": "steer_right"}]})
    with pytest.raises(Exception):
        pass  # placeholder removido abaixo
```

> **Atenção:** os testes de direção usam a ação `steer`, que é registrada aqui. Substitua o último teste por:

```python
def test_comentario_de_direita_empurra_a_intencao():
    engine, game, _ = _montar(
        {"comments": [{"contains": "direita", "action": "steer", "amount": 1}]}
    )
    engine.process(LiveEvent(type=EventType.COMMENT, username="m", text="direita"))
    assert game.intent() > 0


def test_comentario_de_esquerda_empurra_para_o_outro_lado():
    engine, game, _ = _montar(
        {"comments": [{"contains": "esquerda", "action": "steer", "amount": -1}]}
    )
    engine.process(LiveEvent(type=EventType.COMMENT, username="m", text="esquerda"))
    assert game.intent() < 0


def test_horda_de_direita_nao_estoura_a_intencao():
    engine, game, _ = _montar(
        {"comments": [{"contains": "direita", "action": "steer", "amount": 1, "per_user_cooldown": 0}]}
    )
    for i in range(500):
        engine.process(LiveEvent(type=EventType.COMMENT, username=f"u{i}", text="direita"))
    assert abs(game.intent()) <= 3.0


def test_presente_por_nome():
    engine, game, _ = _montar({"gifts": [{"gift": "Rose", "action": "xp", "xp": 5}]})
    engine.process(LiveEvent(type=EventType.GIFT, username="joao", gift_name="Rose"))
    assert game.state.xp == 5


def test_presente_por_id_quando_o_nome_nao_bate():
    engine, game, _ = _montar({"gifts": [{"gift": "Rose", "gift_id": "5655", "action": "xp", "xp": 7}]})
    engine.process(LiveEvent(type=EventType.GIFT, username="j", gift_name="Outro", gift_id="5655"))
    assert game.state.xp == 7


def test_presente_desconhecido_e_ignorado_em_silencio():
    engine, game, _ = _montar({"gifts": [{"gift": "Rose", "action": "xp", "xp": 5}]})
    engine.process(LiveEvent(type=EventType.GIFT, username="j", gift_name="Foguete"))
    assert game.state.xp == 0
    assert game.state.announcements.active() == []


def test_presente_sem_nome_nem_id_e_ignorado():
    engine, game, _ = _montar({"gifts": [{"gift": "Rose", "action": "xp", "xp": 5}]})
    engine.process(LiveEvent(type=EventType.GIFT, username="j", gift_name="", gift_id=None))
    assert game.state.xp == 0


def test_min_quantity_bloqueia_abaixo_do_limite():
    engine, game, _ = _montar(
        {"gifts": [{"gift": "Rose", "action": "xp", "xp": 5, "min_quantity": 10}]}
    )
    engine.process(LiveEvent(type=EventType.GIFT, username="j", gift_name="Rose", quantity=9))
    assert game.state.xp == 0


def test_min_quantity_libera_no_limite():
    engine, game, _ = _montar(
        {"gifts": [{"gift": "Rose", "action": "xp", "xp": 5, "min_quantity": 10}]}
    )
    engine.process(LiveEvent(type=EventType.GIFT, username="j", gift_name="Rose", quantity=10))
    assert game.state.xp == 50


def test_scale_with_quantity_multiplica():
    engine, game, _ = _montar(
        {"gifts": [{"gift": "Rose", "action": "xp", "xp": 5, "scale_with_quantity": True}]}
    )
    engine.process(LiveEvent(type=EventType.GIFT, username="j", gift_name="Rose", quantity=4))
    assert game.state.xp == 20


def test_sem_scale_quantity_o_valor_e_unico():
    engine, game, _ = _montar({"gifts": [{"gift": "Rose", "action": "xp", "xp": 5}]})
    engine.process(LiveEvent(type=EventType.GIFT, username="j", gift_name="Rose", quantity=4))
    assert game.state.xp == 5


def test_max_multiplier_limita_o_estouro():
    engine, game, _ = _montar(
        {"gifts": [{"gift": "Rose", "action": "xp", "xp": 5,
                    "scale_with_quantity": True, "max_multiplier": 10}]}
    )
    engine.process(LiveEvent(type=EventType.GIFT, username="j", gift_name="Rose", quantity=500))
    assert game.state.xp == 50


def test_cooldown_de_presente_bloqueia_repeticao():
    engine, game, relogio = _montar(
        {"gifts": [{"gift": "Rose", "action": "spawn_enemy", "amount": 1, "cooldown": 2.0}]}
    )
    engine.process(LiveEvent(type=EventType.GIFT, username="j", gift_name="Rose"))
    engine.process(LiveEvent(type=EventType.GIFT, username="j", gift_name="Rose"))
    assert len(game.state.enemies) == 1


def test_cooldown_por_usuario_nao_puniu_outro_usuario():
    engine, game, _ = _montar(
        {"gifts": [{"gift": "Rose", "action": "spawn_enemy", "amount": 1, "per_user_cooldown": 5.0}]}
    )
    engine.process(LiveEvent(type=EventType.GIFT, username="joao", gift_name="Rose"))
    engine.process(LiveEvent(type=EventType.GIFT, username="maria", gift_name="Rose"))
    assert len(game.state.enemies) == 2


def test_orcamento_global_segura_rajada_de_usuarios_diferentes():
    engine, game, _ = _montar(
        {"gifts": [{"gift": "Cap", "action": "spawn_enemy", "amount": 1, "per_user_cooldown": 0}]}
    )
    for i in range(50):
        engine.process(LiveEvent(type=EventType.GIFT, username=f"u{i}", gift_name="Cap"))
    assert len(game.state.enemies) == 2  # action_budget["spawn_enemy"] == 2.0


def test_like_milestones_disparam_exatamente_uma_vez_cada():
    engine, game, _ = _montar({"likes": [{"every": 100, "action": "xp", "xp": 20}]})
    engine.process(LiveEvent(type=EventType.LIKE, username="a", like_delta=90, like_total=90))
    assert game.state.xp == 0
    engine.process(LiveEvent(type=EventType.LIKE, username="a", like_delta=260, like_total=350))
    assert game.state.xp == 60  # 100, 200 e 300


def test_repetir_o_mesmo_total_nao_dispara_de_novo():
    engine, game, _ = _montar({"likes": [{"every": 100, "action": "xp", "xp": 20}]})
    engine.process(LiveEvent(type=EventType.LIKE, like_delta=100, like_total=100))
    assert game.state.xp == 20
    engine.process(LiveEvent(type=EventType.LIKE, like_delta=0, like_total=100))
    assert game.state.xp == 20


def test_total_que_regride_e_ignorado():
    engine, game, _ = _montar({"likes": [{"every": 100, "action": "xp", "xp": 20}]})
    engine.process(LiveEvent(type=EventType.LIKE, like_delta=300, like_total=300))
    assert game.state.xp == 60
    engine.process(LiveEvent(type=EventType.LIKE, like_delta=0, like_total=50))
    assert game.state.xp == 60


def test_milestone_com_cooldown_nao_e_engolido():
    # Regressao: o cooldown da regra nao pode descartar o 2o milestone.
    engine, game, _ = _montar(
        {"likes": [{"every": 100, "action": "xp", "xp": 20, "cooldown": 5.0}]}
    )
    engine.process(LiveEvent(type=EventType.LIKE, like_delta=300, like_total=300))
    assert game.state.xp == 60


def test_like_sem_usuario_nao_quebra():
    engine, game, _ = _montar({"likes": [{"every": 100, "action": "xp", "xp": 20}]})
    engine.process(LiveEvent(type=EventType.LIKE, username="", like_delta=150, like_total=150))
    assert game.state.xp == 20


def test_follow_da_xp():
    engine, game, _ = _montar({"follows": [{"action": "xp", "xp": 15}]})
    engine.process(LiveEvent(type=EventType.FOLLOW, username="carlos"))
    assert game.state.xp == 15


def test_share_da_xp():
    engine, game, _ = _montar({"shares": [{"action": "xp", "xp": 10}]})
    engine.process(LiveEvent(type=EventType.SHARE, username="lucas"))
    assert game.state.xp == 10


def test_evento_de_sistema_nao_faz_nada():
    engine, game, _ = _montar({"follows": [{"action": "xp", "xp": 15}]})
    engine.process(LiveEvent(type=EventType.SYSTEM, text="connected"))
    assert game.state.xp == 0


def test_erro_em_uma_regra_nao_derruba_o_processamento():
    engine, game, _ = _montar({"comments": [{"contains": "x", "action": "xp", "xp": "nao e numero"}]})
    engine.process(LiveEvent(type=EventType.COMMENT, username="m", text="x"))
    # Nao levantou; o loop do jogo continua.
    assert game.state.level == 1
```

- [ ] **Step 2: Rodar e ver falhar**

Run: `pytest tests/test_rules.py -v`
Esperado: FAIL — `ImportError: cannot import name 'normalize'` ou assinatura incompatível

- [ ] **Step 3: Implementar**

```python
import logging
import unicodedata

from core.events import EventType, LiveEvent
from core.ratelimit import RateLimiter

logger = logging.getLogger(__name__)


def normalize(text: str) -> str:
    """Minusculo, sem acento e sem espaco nas pontas, para casar comandos."""
    texto = text or ""
    texto = unicodedata.normalize("NFKD", texto)
    texto = "".join(c for c in texto if not unicodedata.combining(c))
    return texto.lower().strip()


class RuleEngine:
    """Traduz LiveEvent em acao do GameEngine.

    Regras novas entram no config.json. Acoes novas entram no registro do
    GameEngine. A integracao com o TikTok nao precisa saber de nada disso.
    """

    def __init__(
        self,
        config: dict,
        game,
        limiter: RateLimiter | None = None,
        on_event=None,
    ):
        self.rules = config["rules"]
        self.game = game
        self.limiter = limiter or RateLimiter()
        self.on_event = on_event

        # Likes: fonte da verdade e o total acumulado da sala. Guardamos o
        # maior total ja visto e o maior milestone ja disparado por regra.
        self._like_max = 0
        self._like_ms: dict[int, int] = {}

    # ---------- entrada ----------

    def process(self, event: LiveEvent) -> None:
        try:
            if event.type == EventType.GIFT:
                self._gift(event)
            elif event.type == EventType.COMMENT:
                self._comment(event)
            elif event.type == EventType.LIKE:
                self._like(event)
            elif event.type == EventType.FOLLOW:
                self._simple("follows", event, "follow")
            elif event.type == EventType.SHARE:
                self._simple("shares", event, "share")
            else:
                logger.debug("Evento sem regra: %s", event.type)
        except Exception:
            # Uma regra mal configurada nao pode derrubar o loop do jogo.
            logger.exception("Erro processando evento %s", event.type)

        if self.on_event is not None:
            try:
                self.on_event(event)
            except Exception:
                logger.exception("Erro no gancho de log de evento")

    # ---------- presentes ----------

    def _gift(self, event: LiveEvent) -> None:
        nome = normalize(event.gift_name)
        for indice, rule in enumerate(self.rules.get("gifts", [])):
            nome_cfg = normalize(rule.get("gift", ""))
            id_cfg = rule.get("gift_id")

            casa_id = (
                id_cfg is not None
                and event.gift_id is not None
                and str(id_cfg) == str(event.gift_id)
            )
            casa_nome = bool(nome_cfg) and nome_cfg == nome

            if casa_id or casa_nome:
                self._run_action(rule, event, f"gift:{indice}:{nome_cfg or id_cfg}")
                return

    # ---------- comentarios ----------

    def _comment(self, event: LiveEvent) -> None:
        texto = normalize(event.text)
        if not texto:
            return
        for indice, rule in enumerate(self.rules.get("comments", [])):
            termo = normalize(rule.get("contains", ""))
            if termo and termo in texto:
                self._run_action(rule, event, f"comment:{indice}:{termo}")

    # ---------- likes ----------

    def _like(self, event: LiveEvent) -> None:
        total = max(self._like_max, int(event.like_total or 0))
        self._like_max = total

        for indice, rule in enumerate(self.rules.get("likes", [])):
            every = int(rule.get("every", 0))
            if every <= 0:
                continue

            marco_atual = total // every
            marco_anterior = self._like_ms.get(indice, 0)
            if marco_atual <= marco_anterior:
                continue

            disparos = marco_atual - marco_anterior
            self._like_ms[indice] = marco_atual

            # Cada milestone cruzado dispara UMA vez. O cooldown da regra
            # NAO participa desta decisao: se participasse, o 2o milestone
            # da mesma rajada seria descartado em silencio.
            for _ in range(disparos):
                payload = self._payload(rule, event, multiplier=1)
                self.game.apply_action(rule["action"], payload, event)

            logger.info(
                "LIKE MILESTONE | total=%s | every=%s | disparos=%s",
                total,
                every,
                disparos,
            )

    # ---------- follow e share ----------

    def _simple(self, secao: str, event: LiveEvent, chave: str) -> None:
        for indice, rule in enumerate(self.rules.get(secao, [])):
            self._run_action(rule, event, f"{chave}:{indice}")

    # ---------- execucao ----------

    def _payload(self, rule: dict, event: LiveEvent, multiplier: int = 1) -> dict:
        payload = dict(rule)
        payload["amount"] = int(rule.get("amount", 1)) * multiplier
        payload["xp"] = int(rule.get("xp", 0)) * multiplier
        return payload

    def _run_action(self, rule: dict, event: LiveEvent, chave: str) -> None:
        acao = rule.get("action")
        if not acao:
            return

        if event.type == EventType.GIFT and not self._passa_min_quantity(rule, event):
            return

        multiplicador = self._multiplicador(rule, event)

        permitido = self.limiter.allow_rule(
            rule_key=chave,
            cooldown=float(rule.get("cooldown", 0)),
            actor=event.actor(),
            per_user_cooldown=float(rule.get("per_user_cooldown", 0)),
        )
        if not permitido:
            return

        if not self.limiter.allow_action(acao):
            logger.debug("Orcamento global esgotado para a acao %s", acao)
            return

        payload = self._payload(rule, event, multiplicador)
        self.game.apply_action(acao, payload, event)

        logger.info(
            "ACTION | usuario=%s | evento=%s | presente=%s | qtd=%s | acao=%s",
            event.actor(),
            event.type,
            event.gift_name,
            event.quantity,
            acao,
        )

    @staticmethod
    def _passa_min_quantity(rule: dict, event: LiveEvent) -> bool:
        minimo = int(rule.get("min_quantity", 1))
        return max(1, event.quantity) >= minimo

    @staticmethod
    def _multiplicador(rule: dict, event: LiveEvent) -> int:
        if not rule.get("scale_with_quantity"):
            return 1
        teto = int(rule.get("max_multiplier", 1))
        return max(1, min(max(1, event.quantity), max(1, teto)))
```

- [ ] **Step 4: Registrar a ação `steer` em `game/engine.py`**

Adicionar ao fim do arquivo, junto das outras ações:

```python
@register("steer")
def _acao_steer(engine: GameEngine, payload: dict, event: LiveEvent) -> None:
    """Direcao vinda de comentario. `amount` negativo vai para a esquerda."""
    engine.steer(float(payload.get("amount", 1)))
    _anunciar(engine, event, "comandou", "DIREITA" if payload.get("amount", 1) > 0 else "ESQUERDA")
```

E adicionar `"steer"` à lista de ações válidas no `test_actions.py::test_todas_as_acoes_do_contrato_existem`? **Não** — `steer` é uma ação de controle por comentário, não uma das 12 do contrato. O teste existente continua correto; apenas garanta que ele usa `<=` (subconjunto), como já está escrito.

- [ ] **Step 5: Atualizar o `test_actions.py` para refletir a contagem**

Nenhuma mudança necessária — o teste usa `esperadas <= known_actions()`, então `steer` extra não quebra.

- [ ] **Step 6: Rodar e ver passar**

Run: `pytest tests/test_rules.py -v`
Esperado: 27 passed

- [ ] **Step 7: Rodar a suíte inteira**

Run: `pytest -v`

- [ ] **Step 8: Commitar**

```bash
git add core/rules.py game/engine.py tests/test_rules.py
git commit -m "Reescreve o motor de regras com likes idempotentes e anti-spam em camadas"
```

---

### Task 11: `core/logging_setup.py`

**Files:**
- Create: `core/logging_setup.py`
- Test: `tests/test_logging_setup.py`

**Interfaces:**
- Consumes: `core.events.LiveEvent`
- Produces: `setup_logging(log_dir="logs", level=logging.INFO) -> logging.Logger`; `EventJournal(path)` com `record(event) -> None` e `close()`

**Contexto:** §17 pede `logs/app.log` com formato legível; §9/§10 pedem registrar follow e share com username, horário e ação. Sem rotação, uma LIVE longa com spam gera um arquivo enorme.

- [ ] **Step 1: Escrever o teste que falha**

```python
import json
import logging

from core.events import EventType, LiveEvent
from core.logging_setup import EventJournal, setup_logging


def test_setup_cria_o_arquivo_de_log(tmp_path):
    logger = setup_logging(log_dir=tmp_path)
    logger.info("teste")
    for h in logger.handlers:
        h.flush()
    assert (tmp_path / "app.log").exists()


def test_log_usa_formato_com_hora_entre_colchetes(tmp_path):
    logger = setup_logging(log_dir=tmp_path)
    logger.info("GIFT user=joao gift=Rose quantity=1")
    for h in logger.handlers:
        h.flush()
    conteudo = (tmp_path / "app.log").read_text(encoding="utf-8")
    assert "GIFT user=joao gift=Rose quantity=1" in conteudo
    assert conteudo.strip().startswith("[")


def test_setup_e_idempotente(tmp_path):
    a = setup_logging(log_dir=tmp_path)
    b = setup_logging(log_dir=tmp_path)
    assert a is b
    assert len(a.handlers) <= 2  # nao acumula handler a cada chamada


def test_journal_grava_jsonl(tmp_path):
    caminho = tmp_path / "events.jsonl"
    j = EventJournal(caminho)
    j.record(LiveEvent(type=EventType.FOLLOW, username="carlos", display_name="Carlos"))
    j.close()
    linha = caminho.read_text(encoding="utf-8").strip()
    dado = json.loads(linha)
    assert dado["type"] == "follow"
    assert dado["username"] == "carlos"
    assert "timestamp" in dado


def test_journal_grava_share_com_horario(tmp_path):
    caminho = tmp_path / "events.jsonl"
    j = EventJournal(caminho)
    j.record(LiveEvent(type=EventType.SHARE, username="lucas"))
    j.record(LiveEvent(type=EventType.GIFT, username="joao", gift_name="Rose", quantity=2))
    j.close()
    linhas = [json.loads(l) for l in caminho.read_text(encoding="utf-8").splitlines()]
    assert [l["type"] for l in linhas] == ["share", "gift"]
    assert linhas[1]["gift_name"] == "Rose"


def test_journal_ignora_evento_de_sistema(tmp_path):
    caminho = tmp_path / "events.jsonl"
    j = EventJournal(caminho)
    j.record(LiveEvent(type=EventType.SYSTEM, text="connected"))
    j.close()
    assert caminho.read_text(encoding="utf-8").strip() == ""


def test_journal_nao_quebra_se_o_diretorio_sumir(tmp_path):
    caminho = tmp_path / "sub" / "events.jsonl"
    j = EventJournal(caminho)
    j.record(LiveEvent(type=EventType.FOLLOW, username="a"))
    j.close()  # nao pode levantar
```

- [ ] **Step 2: Rodar e ver falhar**

Run: `pytest tests/test_logging_setup.py -v`
Esperado: FAIL — `ModuleNotFoundError: No module named 'core.logging_setup'`

- [ ] **Step 3: Implementar**

```python
import json
import logging
import logging.handlers
from pathlib import Path

from core.events import EventType, LiveEvent

_CONFIGURADO: logging.Logger | None = None

FORMATO = "[%(asctime)s] %(levelname)-7s %(name)s | %(message)s"
FORMATO_DATA = "%H:%M:%S"

TAMANHO_MAX = 5 * 1024 * 1024  # 5 MB
BACKUPS = 3


class _FormatadorHora(logging.Formatter):
    """Hora entre colchetes, sem data: uma LIVE nao dura dias."""

    def formatTime(self, record, datefmt=None):  # noqa: N802 (API do logging)
        return self.formatTime.__wrapped__(record, datefmt) if False else super().formatTime(
            record, datefmt or FORMATO_DATA
        )


def setup_logging(log_dir: str | Path = "logs", level: int = logging.INFO) -> logging.Logger:
    """Configura o log da aplicacao. Chamadas repetidas nao duplicam handlers."""
    global _CONFIGURADO
    if _CONFIGURADO is not None:
        return _CONFIGURADO

    destino = Path(log_dir)
    destino.mkdir(parents=True, exist_ok=True)

    arquivo = logging.handlers.RotatingFileHandler(
        destino / "app.log",
        maxBytes=TAMANHO_MAX,
        backupCount=BACKUPS,
        encoding="utf-8",
    )
    arquivo.setFormatter(_FormatadorHora(FORMATO, datefmt=FORMATO_DATA))

    console = logging.StreamHandler()
    console.setFormatter(logging.Formatter(FORMATO, datefmt=FORMATO_DATA))

    raiz = logging.getLogger()
    raiz.setLevel(level)
    raiz.handlers.clear()
    raiz.addHandler(arquivo)
    raiz.addHandler(console)

    _CONFIGURADO = raiz
    return raiz


class EventJournal:
    """Log estruturado em JSONL, para consulta posterior.

    Registra apenas eventos com autor: follow, share, gift, comment, like.
    """

    _IGNORADOS = {EventType.SYSTEM}

    def __init__(self, path: str | Path = "logs/events.jsonl"):
        self.path = Path(path)
        self._arquivo = None
        try:
            self.path.parent.mkdir(parents=True, exist_ok=True)
            self._arquivo = self.path.open("a", encoding="utf-8")
        except OSError:
            self._arquivo = None

    def record(self, event: LiveEvent) -> None:
        if self._arquivo is None or event.type in self._IGNORADOS:
            return
        linha = {
            "timestamp": event.timestamp.isoformat(),
            "type": str(event.type),
            "username": event.username,
            "display_name": event.display_name,
            "text": event.text,
            "gift_name": event.gift_name,
            "gift_id": event.gift_id,
            "quantity": event.quantity,
            "like_delta": event.like_delta,
            "like_total": event.like_total,
        }
        try:
            self._arquivo.write(json.dumps(linha, ensure_ascii=False) + "\n")
            self._arquivo.flush()
        except OSError:
            pass  # disco cheio nao pode derrubar a LIVE

    def close(self) -> None:
        if self._arquivo is not None:
            try:
                self._arquivo.close()
            except OSError:
                pass
            self._arquivo = None
```

> O `_FormatadorHora` acima ficou confuso. Substitua-o por um simples:

```python
def _formatador() -> logging.Formatter:
    return logging.Formatter(FORMATO, datefmt=FORMATO_DATA)
```

e use `_formatador()` nos dois handlers. O resultado é `[09:16:01] INFO    core.rules | ACTION ...`.

- [ ] **Step 4: Rodar e ver passar**

Run: `pytest tests/test_logging_setup.py -v`
Esperado: 7 passed

- [ ] **Step 5: Commitar**

```bash
git add core/logging_setup.py tests/test_logging_setup.py
git commit -m "Adiciona log com rotacao e journal JSONL de eventos"
```

---

### Task 12: `adapters/base.py` e `adapters/simulated.py`

**Files:**
- Create: `adapters/base.py`, `adapters/simulated.py`
- Modify: `adapters/__init__.py` (vazio, mantém)
- Test: `tests/test_simulated.py`

**Interfaces:**
- Consumes: `core.events.LiveEvent`, `core.event_queue.EventQueue`
- Produces: `LiveAdapter` (Protocol com `start()`, `stop()`, `status`), `AdapterStatus` (dataclass com `connected: bool`, `detail: str`), `SimulatedAdapter(queue, config)`, `parse_command(line) -> LiveEvent | None`, `run_burst(queue, config, count) -> None`

**Contexto:** §21/§22 — o modo teste troca **só o adapter**. Mesma fila, mesmas regras, mesmo jogo. É isso que impede teste e produção de divergirem.

- [ ] **Step 1: Escrever o teste que falha**

```python
import time

from adapters.simulated import SimulatedAdapter, parse_command, run_burst
from core.event_queue import EventQueue
from core.events import EventType

CONFIG = {"tiktok": {"username": "@teste"}, "app": {"queue_max_size": 100}}


def _q():
    return EventQueue(maxsize=1000)


def test_parse_gift_por_nome():
    e = parse_command("Rose")
    assert e.type == EventType.GIFT
    assert e.gift_name == "Rose"
    assert e.quantity == 1


def test_parse_gift_com_quantidade():
    e = parse_command("Rose 10")
    assert e.gift_name == "Rose"
    assert e.quantity == 10


def test_parse_comentario_com_aspas():
    e = parse_command('"corre"')
    assert e.type == EventType.COMMENT
    assert e.text == "corre"


def test_parse_comentario_com_prefixo():
    e = parse_command("corre")
    assert e.type == EventType.COMMENT
    assert e.text == "corre"


def test_parse_follow():
    assert parse_command("follow").type == EventType.FOLLOW


def test_parse_share():
    assert parse_command("share").type == EventType.SHARE


def test_parse_like_com_contador():
    e = parse_command("like 100")
    assert e.type == EventType.LIKE
    assert e.like_delta == 100
    assert e.like_total == 100


def test_parse_like_acumula_entre_comandos():
    q = _q()
    a = SimulatedAdapter(q, CONFIG)
    a.handle_line("like 100")
    a.handle_line("like 50")
    eventos = [q.get_nowait() for _ in range(2)]
    assert eventos[0].like_total == 100
    assert eventos[1].like_total == 150
    assert eventos[1].like_delta == 50


def test_parse_user_troca_o_autor():
    e = parse_command("user joao Rose")
    assert e.username == "joao"
    assert e.gift_name == "Rose"


def test_parse_help_retorna_none():
    assert parse_command("help") is None


def test_parse_vazio_retorna_none():
    assert parse_command("") is None
    assert parse_command("   ") is None


def test_parse_desconhecido_vira_comentario():
    e = parse_command("bom dia galera")
    assert e.type == EventType.COMMENT
    assert e.text == "bom dia galera"


def test_adapter_escreve_na_fila():
    q = _q()
    a = SimulatedAdapter(q, CONFIG)
    a.handle_line("follow")
    assert q.get_nowait().type == EventType.FOLLOW


def test_burst_nao_bloqueia_e_respeita_o_limite_da_fila():
    q = EventQueue(maxsize=50)
    run_burst(q, CONFIG, count=500)
    assert q.size() <= 50
    assert q.dropped > 0


def test_adapter_start_e_stop_sem_travar():
    q = _q()
    a = SimulatedAdapter(q, CONFIG, interactive=False)
    a.start()
    time.sleep(0.05)
    a.stop()
    assert not a.status.connected


def test_status_reflete_o_estado():
    a = SimulatedAdapter(_q(), CONFIG, interactive=False)
    assert not a.status.connected
```

- [ ] **Step 2: Rodar e ver falhar**

Run: `pytest tests/test_simulated.py -v`
Esperado: FAIL — `ModuleNotFoundError: No module named 'adapters.simulated'`

- [ ] **Step 3: Implementar `adapters/base.py`**

```python
from dataclasses import dataclass
from typing import Protocol, runtime_checkable


@dataclass
class AdapterStatus:
    """Estado da conexao, exibido no HUD."""

    connected: bool = False
    detail: str = "desconectado"
    reconnects: int = 0


@runtime_checkable
class LiveAdapter(Protocol):
    """Fonte de eventos.

    Implementado por `TikTokLiveAdapter` (LIVE real) e `SimulatedAdapter`
    (modo teste). O resto do sistema nao sabe qual dos dois esta ativo.
    """

    def start(self) -> None: ...

    def stop(self) -> None: ...

    @property
    def status(self) -> AdapterStatus: ...
```

- [ ] **Step 4: Implementar `adapters/simulated.py`**

```python
import logging
import random
import threading
import time

from adapters.base import AdapterStatus
from core.event_queue import EventQueue
from core.events import EventType, LiveEvent

logger = logging.getLogger(__name__)

PRESENTES_EXEMPLO = [
    "Rose", "Heart Me", "GG", "Finger Heart", "Ice Cream Cone",
    "Doughnut", "Perfume", "Cap", "Confetti", "TikTok", "Lion",
]
COMANDOS_EXEMPLO = ["corre", "pula", "direita", "esquerda", "xp"]

USUARIOS_EXEMPLO = ["joao", "maria", "pedro", "ana", "carlos", "lucas", "bia"]

AJUDA = """Comandos do modo teste:
  Rose                presente (o nome tem que existir no config.json)
  Rose 10             presente com quantidade 10
  GG                  outro presente
  corre               comentario
  "bom dia"           comentario entre aspas
  follow              novo seguidor
  share               compartilhamento
  like 100            cem curtidas
  user joao Rose      define o autor e envia
  auto                rajada aleatoria de eventos
  help                esta ajuda
  quit                sair"""


class SimulatedAdapter:
    """Adapter de teste. Escreve na MESMA fila que o adapter real.

    Nao ha conexao com o TikTok: os eventos sao digitados ou sorteados.
    """

    def __init__(
        self,
        queue: EventQueue,
        config: dict,
        interactive: bool = True,
    ):
        self.queue = queue
        self.config = config
        self.interactive = interactive

        self._status = AdapterStatus(connected=False, detail="modo teste")
        self._stop = threading.Event()
        self._thread: threading.Thread | None = None

        self._like_total = 0
        self._autor = random.choice(USUARIOS_EXEMPLO)

    @property
    def status(self) -> AdapterStatus:
        return self._status

    def start(self) -> None:
        self._status = AdapterStatus(connected=True, detail="modo teste")
        logger.info("Modo TESTE ativo. Nenhuma conexao com o TikTok.")
        if self.interactive:
            print(AJUDA)
        self._thread = threading.Thread(target=self._loop, name="simulado", daemon=True)
        self._thread.start()

    def stop(self) -> None:
        self._stop.set()
        self._status = AdapterStatus(connected=False, detail="encerrado")
        if self._thread is not None and self._thread.is_alive():
            self._thread.join(timeout=1.0)

    def _loop(self) -> None:
        while not self._stop.is_set():
            try:
                linha = input()
            except (EOFError, KeyboardInterrupt):
                break
            except Exception:
                time.sleep(0.1)
                continue

            if linha.strip().lower() in {"quit", "sair", "exit"}:
                self._stop.set()
                break
            if linha.strip().lower() == "auto":
                run_burst(self.queue, self.config, count=50)
                continue
            if linha.strip().lower() == "help":
                print(AJUDA)
                continue

            evento = self.handle_line(linha)
            if evento is None and linha.strip():
                print("Nao entendi. Digite 'help'.")

    # ---------- traducao de linha em evento ----------

    def handle_line(self, linha: str) -> LiveEvent | None:
        evento = parse_command(linha, autor=self._autor, like_total=self._like_total)
        if evento is None:
            return None

        if evento.type == EventType.LIKE:
            self._like_total = evento.like_total
        elif evento.username:
            self._autor = evento.username

        logger.info(
            "SIMULADO | tipo=%s | autor=%s | texto=%s | presente=%s | qtd=%s",
            evento.type,
            evento.actor(),
            evento.text,
            evento.gift_name,
            evento.quantity,
        )
        self.queue.put(evento)
        return evento


def parse_command(
    linha: str,
    autor: str = "voce",
    like_total: int = 0,
) -> LiveEvent | None:
    """Traduz uma linha digitada em LiveEvent.

    Retorna None para linhas vazias ou de controle (help/quit/auto).
    """
    texto = (linha or "").strip()
    if not texto:
        return None

    partes = texto.split()
    primeiro = partes[0].lower()

    if primeiro in {"help", "quit", "sair", "exit", "auto"}:
        return None

    if primeiro == "user" and len(partes) >= 2:
        autor = partes[1]
        resto = " ".join(partes[2:]).strip()
        if not resto:
            return None
        return parse_command(resto, autor=autor, like_total=like_total)

    if primeiro == "follow":
        return LiveEvent(type=EventType.FOLLOW, username=autor, display_name=autor)

    if primeiro == "share":
        return LiveEvent(type=EventType.SHARE, username=autor, display_name=autor)

    if primeiro == "like":
        delta = 1
        if len(partes) >= 2:
            try:
                delta = max(1, int(partes[1]))
            except ValueError:
                delta = 1
        total = like_total + delta
        return LiveEvent(
            type=EventType.LIKE,
            username=autor,
            display_name=autor,
            like_delta=delta,
            like_total=total,
            quantity=delta,
        )

    # Comentario entre aspas: o resto inteiro e o texto.
    if texto.startswith('"') and texto.endswith('"') and len(texto) > 1:
        return LiveEvent(
            type=EventType.COMMENT, username=autor, display_name=autor, text=texto[1:-1]
        )

    # "NomeDoPresente [qtd]" quando a primeira palavra nao e um comando.
    if primeiro not in COMANDOS_EXEMPLO and len(partes) <= 2:
        quantidade = 1
        if len(partes) == 2:
            try:
                quantidade = max(1, int(partes[1]))
                return LiveEvent(
                    type=EventType.GIFT,
                    username=autor,
                    display_name=autor,
                    gift_name=partes[0],
                    quantity=quantidade,
                )
            except ValueError:
                pass
        return LiveEvent(
            type=EventType.GIFT,
            username=autor,
            display_name=autor,
            gift_name=partes[0],
            quantity=quantidade,
        )

    return LiveEvent(type=EventType.COMMENT, username=autor, display_name=autor, text=texto)


def run_burst(queue: EventQueue, config: dict, count: int = 500) -> None:
    """Rajada aleatoria. Existe para PROVAR o anti-spam: se travar, falhou."""
    total_likes = 0
    for i in range(count):
        autor = random.choice(USUARIOS_EXEMPLO)
        escolha = random.random()

        if escolha < 0.45:
            evento = LiveEvent(
                type=EventType.GIFT,
                username=autor,
                display_name=autor,
                gift_name=random.choice(PRESENTES_EXEMPLO),
                quantity=random.choice([1, 1, 1, 5, 10, 100]),
            )
        elif escolha < 0.75:
            evento = LiveEvent(
                type=EventType.COMMENT,
                username=autor,
                display_name=autor,
                text=random.choice(COMANDOS_EXEMPLO),
            )
        elif escolha < 0.9:
            total_likes += random.randint(1, 20)
            evento = LiveEvent(
                type=EventType.LIKE,
                username=autor,
                display_name=autor,
                like_delta=random.randint(1, 20),
                like_total=total_likes,
            )
        elif escolha < 0.96:
            evento = LiveEvent(type=EventType.FOLLOW, username=autor, display_name=autor)
        else:
            evento = LiveEvent(type=EventType.SHARE, username=autor, display_name=autor)

        queue.put(evento)

    logger.info("Rajada de %s eventos enviada.", count)
```

- [ ] **Step 5: Rodar e ver passar**

Run: `pytest tests/test_simulated.py -v`
Esperado: 16 passed

- [ ] **Step 6: Commitar**

```bash
git add adapters/base.py adapters/simulated.py tests/test_simulated.py
git commit -m "Adiciona protocolo de adapter e adapter simulado do modo teste"
```

---

### Task 13: `adapters/tiktok_live.py` — integração real

**Files:**
- Modify: `adapters/tiktok_live.py` (reescrita)
- Test: `tests/test_tiktok_mapping.py`

**Interfaces:**
- Consumes: `adapters.base.{LiveAdapter, AdapterStatus}`, `core.event_queue.EventQueue`, `core.events.LiveEvent`
- Produces: `TikTokLiveAdapter(queue, config)` com `start()`, `stop()`, `status`; e as funções **puras** `evento_de_comentario(obj, autor_anterior)`, `evento_de_presente(obj)`, `evento_de_like(obj, total_anterior)`, testáveis sem rede

**Contexto:** o TikTokLive é assíncrono e não testável sem LIVE. Por isso a tradução de evento bruto → `LiveEvent` sai em funções puras que recebem um objeto simples. Os testes usam dublês.

Correções sobre o código atual:
1. `await client.close()` dentro do loop asyncio levanta `RuntimeError` → usar `await client.disconnect()`.
2. `except Exception` genérico engole tudo → tratar os erros específicos.
3. Reconexão fixa de 5 s → backoff exponencial com jitter.
4. Criar cliente novo a cada tentativa (obrigatório: o cliente não é reutilizável).

- [ ] **Step 1: Escrever o teste que falha**

```python
from adapters.tiktok_live import evento_de_comentario, evento_de_like, evento_de_presente
from core.events import EventType


class UsuarioFalso:
    def __init__(self, unique_id="joao", nickname="João"):
        self.unique_id = unique_id
        self.nickname = nickname


class PresenteFalso:
    def __init__(self, name="Rose", type=1, diamond_count=1):
        self.name = name
        self.type = type
        self.diamond_count = diamond_count


class ComentarioFalso:
    def __init__(self, content="corre", user=None):
        self.content = content
        self.user = user if user is not None else UsuarioFalso()
        self.comment = content  # alias de leitura


class PresenteEventoFalso:
    def __init__(self, user=None, gift=None, repeat_count=1, repeat_end=1, streaking=False):
        self.user = user if user is not None else UsuarioFalso()
        self.gift = gift if gift is not None else PresenteFalso()
        self.repeat_count = repeat_count
        self.repeat_end = repeat_end
        self.streaking = streaking


class LikeEventoFalso:
    def __init__(self, user=None, count=1, total=1):
        self.user = user
        self.count = count
        self.total = total


def test_comentario_usa_content_e_user():
    e = evento_de_comentario(ComentarioFalso(content="corre"))
    assert e.type == EventType.COMMENT
    assert e.text == "corre"
    assert e.username == "joao"
    assert e.display_name == "João"


def test_comentario_com_user_none_nao_quebra():
    e = evento_de_comentario(ComentarioFalso(user=None))
    e.user = None
    e2 = evento_de_comentario(type("X", (), {"content": "oi", "user": None})())
    assert e2.username == ""
    assert e2.actor() == "desconhecido"


def test_presente_streak_em_andamento_e_ignorado():
    obj = PresenteEventoFalso(streaking=True, repeat_end=0, repeat_count=5)
    assert evento_de_presente(obj) is None


def test_presente_streakable_final_e_processado():
    obj = PresenteEventoFalso(gift=PresenteFalso(type=1), streaking=False, repeat_end=1, repeat_count=20)
    e = evento_de_presente(obj)
    assert e is not None
    assert e.quantity == 20


def test_presente_nao_streakable_e_processado_uma_vez():
    # gift.type != 1 significa nao-streakable: streaking tambem e False.
    obj = PresenteEventoFalso(gift=PresenteFalso(type=2), streaking=False, repeat_count=1)
    e = evento_de_presente(obj)
    assert e is not None
    assert e.quantity == 1


def test_presente_sem_gift_e_ignorado():
    assert evento_de_presente(PresenteEventoFalso(gift=None)) is None


def test_like_usa_count_como_delta_e_total_como_acumulado():
    e = evento_de_like(LikeEventoFalso(count=5, total=120), total_anterior=100)
    assert e.like_delta == 5
    assert e.like_total == 120


def test_like_sem_usuario_nao_quebra():
    e = evento_de_like(LikeEventoFalso(user=None, count=3, total=50), total_anterior=0)
    assert e.username == ""
    assert e.actor() == "desconhecido"
    assert e.like_total == 50


def test_like_com_total_menor_que_o_anterior_e_ignorado():
    e = evento_de_like(LikeEventoFalso(count=1, total=10), total_anterior=100)
    assert e.like_total == 100
```

- [ ] **Step 2: Rodar e ver falhar**

Run: `pytest tests/test_tiktok_mapping.py -v`
Esperado: FAIL — `ImportError: cannot import name 'evento_de_comentario'`

- [ ] **Step 3: Implementar**

```python
import asyncio
import logging
import random
import threading
from typing import Any

from adapters.base import AdapterStatus
from core.event_queue import EventQueue
from core.events import EventType, LiveEvent

logger = logging.getLogger(__name__)

# A biblioteca NAO tem reconexao propria: `run()` retorna em fim limpo e
# levanta em queda, e o cliente nao pode ser reutilizado. Por isso o laco
# externo cria um cliente novo a cada tentativa.
BACKOFF_INICIAL = 5.0
BACKOFF_MAX = 60.0


# ---------------------------------------------------------------------------
# Traducao evento bruto -> LiveEvent. Funcoes puras: testaveis sem rede.
# ---------------------------------------------------------------------------


def _user_id(user: Any) -> str:
    if user is None:
        return ""
    return str(getattr(user, "unique_id", None) or getattr(user, "display_id", None) or "")


def _display_name(user: Any) -> str:
    if user is None:
        return ""
    return str(
        getattr(user, "nickname", None)
        or getattr(user, "display_name", None)
        or _user_id(user)
    )


def evento_de_comentario(obj: Any) -> LiveEvent:
    user = getattr(obj, "user", None)
    # v3 renomeou `comment` para `content`; o alias antigo ainda existe.
    texto = getattr(obj, "content", None) or getattr(obj, "comment", "") or ""
    return LiveEvent(
        type=EventType.COMMENT,
        username=_user_id(user),
        display_name=_display_name(user),
        text=str(texto),
        raw=obj,
    )


def evento_de_presente(obj: Any) -> LiveEvent | None:
    """Traduz um GiftEvent. Retorna None para eventos que devem ser ignorados.

    Detalhe verificado: `event.streaking` e False TANTO no evento final de um
    streak QUANTO em todo presente nao-streakable. `gift.type == 1` e o que
    distingue os dois casos.
    """
    gift = getattr(obj, "gift", None)
    if gift is None:
        return None

    if getattr(obj, "streaking", False):
        return None  # evento intermediario de streak

    user = getattr(obj, "user", None)
    quantidade = int(
        getattr(obj, "repeat_count", 1)
        or getattr(obj, "combo_count", 1)
        or 1
    )
    gift_id = getattr(gift, "id", None) or getattr(obj, "gift_id", None)

    return LiveEvent(
        type=EventType.GIFT,
        username=_user_id(user),
        display_name=_display_name(user),
        gift_name=str(getattr(gift, "name", "") or getattr(gift, "gift_name", "") or ""),
        gift_id=str(gift_id) if gift_id is not None else None,
        quantity=max(1, quantidade),
        raw=obj,
    )


def evento_de_like(obj: Any, total_anterior: int = 0) -> LiveEvent | None:
    """Traduz um LikeEvent.

    `count` e o incremento do evento; `total` e o acumulado da sala. O
    TikTok agrupa curtidas, entao um evento nao e uma curtida. O total e
    monotono: um valor menor que o ja visto e descartado.

    `user` pode vir None: o TikTok limita eventos de like por usuario
    depois de ~10-20, e o total continua subindo.
    """
    user = getattr(obj, "user", None)
    delta = max(0, int(getattr(obj, "count", 0) or 0))
    total = int(getattr(obj, "total", 0) or 0)

    if total < total_anterior:
        total = total_anterior
        delta = 0
    if total == 0 and delta == 0:
        return None

    return LiveEvent(
        type=EventType.LIKE,
        username=_user_id(user),
        display_name=_display_name(user),
        like_delta=delta,
        like_total=total,
        quantity=delta,
        raw=obj,
    )


# ---------------------------------------------------------------------------
# Adapter
# ---------------------------------------------------------------------------


class TikTokLiveAdapter:
    """Integracao real. TikTokLive e engenharia reversa do Webcast interno:
    nao e API oficial e pode quebrar sem aviso. Todo o resto do sistema
    ignora isso, porque so este arquivo importa a biblioteca.
    """

    def __init__(self, queue: EventQueue, config: dict):
        self.queue = queue
        cfg = config.get("tiktok", {})
        self.username = str(cfg.get("username", "")).lstrip("@")
        self.backoff_inicial = float(cfg.get("reconnect_seconds", BACKOFF_INICIAL))
        self.backoff_max = float(cfg.get("reconnect_max_seconds", BACKOFF_MAX))
        self.fetch_gift_info = bool(cfg.get("fetch_gift_info", True))

        self._status = AdapterStatus(connected=False, detail="iniciando")
        self._stop = threading.Event()
        self._thread: threading.Thread | None = None
        self._like_total = 0

    @property
    def status(self) -> AdapterStatus:
        return self._status

    def start(self) -> None:
        self._thread = threading.Thread(target=self._thread_main, name="tiktok", daemon=True)
        self._thread.start()

    def stop(self) -> None:
        self._stop.set()
        if self._thread is not None and self._thread.is_alive():
            self._thread.join(timeout=3.0)

    def _thread_main(self) -> None:
        try:
            asyncio.run(self._run_forever())
        except Exception:
            logger.exception("Thread do TikTok encerrou com erro")

    async def _run_forever(self) -> None:
        from TikTokLive import TikTokLiveClient
        from TikTokLive.client.errors import (
            UserNotFoundError,
            UserOfflineError,
            WebcastBlockedError,
        )
        from TikTokLive.events import (
            CommentEvent,
            ConnectEvent,
            DisconnectEvent,
            FollowEvent,
            GiftEvent,
            LikeEvent,
            ShareEvent,
        )

        tentativa = 0
        backoff = self.backoff_inicial

        while not self._stop.is_set():
            client = None
            try:
                # Cliente NOVO a cada tentativa: o cliente nao e reutilizavel.
                client = TikTokLiveClient(unique_id=self.username)
                self._registrar_handlers(
                    client,
                    CommentEvent=CommentEvent,
                    ConnectEvent=ConnectEvent,
                    DisconnectEvent=DisconnectEvent,
                    FollowEvent=FollowEvent,
                    GiftEvent=GiftEvent,
                    LikeEvent=LikeEvent,
                    ShareEvent=ShareEvent,
                )

                logger.info("Conectando a LIVE @%s (tentativa %s)", self.username, tentativa + 1)
                self._status = AdapterStatus(connected=False, detail="conectando", reconnects=tentativa)

                await client.connect(
                    fetch_gift_info=self.fetch_gift_info,
                    fetch_room_info=False,
                    fetch_live_check=True,
                )
                # `connect()` retorna quando a transmissao termina em paz.
                logger.info("LIVE encerrou ou caiu de forma limpa.")
                tentativa = 0
                backoff = self.backoff_inicial

            except UserNotFoundError:
                logger.error("Usuario @%s nao existe. Corrija o config.json.", self.username)
                self._status = AdapterStatus(connected=False, detail="usuario invalido")
                return  # nao adianta tentar de novo
            except UserOfflineError:
                logger.info("Usuario @%s nao esta ao vivo. Nova checagem em 30s.", self.username)
                self._status = AdapterStatus(connected=False, detail="fora do ar")
                await self._dormir(30.0)
                continue
            except WebcastBlockedError:
                logger.warning("TikTok bloqueou o Webcast. Nova tentativa em 60s.")
                self._status = AdapterStatus(connected=False, detail="bloqueado")
                await self._dormir(60.0)
                continue
            except asyncio.CancelledError:
                break
            except Exception as erro:
                tentativa += 1
                espera = self._espera(backoff, tentativa)
                logger.warning(
                    "Falha na conexao (%s). Tentando em %.1fs (tentativa %s).",
                    type(erro).__name__,
                    espera,
                    tentativa,
                )
                self._status = AdapterStatus(
                    connected=False, detail="reconectando", reconnects=tentativa
                )
                await self._dormir(espera)
                backoff = min(self.backoff_max, backoff * 2)
            finally:
                if client is not None and self._stop.is_set():
                    # `await client.close()` levantaria RuntimeError, porque
                    # close() chama run_until_complete() num loop ja rodando.
                    try:
                        await client.disconnect()
                    except Exception:
                        logger.debug("Falha ao desconectar o cliente", exc_info=True)

            if self._stop.is_set():
                break

        self._status = AdapterStatus(connected=False, detail="encerrado", reconnects=tentativa)

    def _espera(self, backoff: float, tentativa: int) -> float:
        """Backoff exponencial com jitter, para nao reconectar em rebanho."""
        base = min(self.backoff_max, backoff)
        return base * (0.5 + random.random())

    async def _dormir(self, segundos: float) -> None:
        """Dorme em fatias curtas para que stop() responda rapido."""
        fim = asyncio.get_running_loop().time() + segundos
        while not self._stop.is_set():
            restante = fim - asyncio.get_running_loop().time()
            if restante <= 0:
                return
            await asyncio.sleep(min(0.25, restante))

    def _registrar_handlers(self, client, **eventos) -> None:
        ConnectEvent = eventos["ConnectEvent"]
        DisconnectEvent = eventos["DisconnectEvent"]
        CommentEvent = eventos["CommentEvent"]
        GiftEvent = eventos["GiftEvent"]
        LikeEvent = eventos["LikeEvent"]
        FollowEvent = eventos["FollowEvent"]
        ShareEvent = eventos["ShareEvent"]

        @client.on(ConnectEvent)
        async def on_connect(event):
            logger.info("CONNECTED | @%s | room=%s", self.username, getattr(client, "room_id", "?"))
            self._status = AdapterStatus(connected=True, detail="ao vivo")
            self.queue.put(LiveEvent(type=EventType.SYSTEM, text="connected"))

        @client.on(DisconnectEvent)
        async def on_disconnect(event):
            logger.warning("DISCONNECTED | o WebSocket do TikTok caiu")
            self._status = AdapterStatus(connected=False, detail="desconectado")
            self.queue.put(LiveEvent(type=EventType.SYSTEM, text="disconnected"))

        @client.on(CommentEvent)
        async def on_comment(event):
            self.queue.put(evento_de_comentario(event))

        @client.on(GiftEvent)
        async def on_gift(event):
            traduzido = evento_de_presente(event)
            if traduzido is not None:
                self.queue.put(traduzido)

        @client.on(LikeEvent)
        async def on_like(event):
            traduzido = evento_de_like(event, total_anterior=self._like_total)
            if traduzido is not None:
                self._like_total = traduzido.like_total
                self.queue.put(traduzido)

        @client.on(FollowEvent)
        async def on_follow(event):
            user = getattr(event, "user", None)
            self.queue.put(
                LiveEvent(
                    type=EventType.FOLLOW,
                    username=_user_id(user),
                    display_name=_display_name(user),
                    raw=event,
                )
            )

        @client.on(ShareEvent)
        async def on_share(event):
            user = getattr(event, "user", None)
            self.queue.put(
                LiveEvent(
                    type=EventType.SHARE,
                    username=_user_id(user),
                    display_name=_display_name(user),
                    raw=event,
                )
            )
```

- [ ] **Step 4: Rodar e ver passar**

Run: `pytest tests/test_tiktok_mapping.py -v`
Esperado: 9 passed

- [ ] **Step 5: Verificar que o TikTokLive é importável e o cliente existe**

```powershell
python -c "from TikTokLive import TikTokLiveClient; import inspect; print(inspect.signature(TikTokLiveClient.__init__))"
python -c "from TikTokLive.events import CommentEvent, GiftEvent, LikeEvent, FollowEvent, ShareEvent, ConnectEvent, DisconnectEvent; print('eventos OK')"
python -c "from TikTokLive.client.errors import UserOfflineError, UserNotFoundError, WebcastBlockedError; print('erros OK')"
```

Esperado: as três linhas imprimem sem erro. Se `TikTokLive.client.errors` não tiver esses nomes, ajuste os imports do `except` — **não invente nomes**.

- [ ] **Step 6: Commitar**

```bash
git add adapters/tiktok_live.py tests/test_tiktok_mapping.py
git commit -m "Reescreve o adapter do TikTok com backoff, erros especificos e traducao testavel"
```

---

### Task 14: `ui/theme.py` e `ui/widgets.py`

**Files:**
- Create: `ui/theme.py`, `ui/widgets.py`
- Test: `tests/test_theme.py`

**Interfaces:**
- Consumes: nada de pygame em `theme.py` (só medidas); `widgets.py` usa pygame
- Produces: `Theme.from_config(config) -> Theme` com `width, height, scale, cores (dict), fontes (dict), rects (dict)`; `TextCache` com `render(text, font_key, color) -> Surface`; `draw_bar`, `draw_panel`, `draw_text`

**Contexto:** o custo real em 1080x1920 é `font.render()` por frame. Sem cache, 60 FPS não se sustenta. `theme.py` fica sem import de pygame para ser testável.

- [ ] **Step 1: Escrever o teste que falha**

```python
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
    assert t.rects["feed"].bottom <= t.height
    assert t.rects["hud"].top == 0


def test_feed_size_vem_do_config():
    assert Theme.from_config(_cfg()).feed_size == 6
```

- [ ] **Step 2: Rodar e ver falhar**

Run: `pytest tests/test_theme.py -v`
Esperado: FAIL — `ModuleNotFoundError: No module named 'ui.theme'`

- [ ] **Step 3: Implementar `ui/theme.py`**

```python
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
```

- [ ] **Step 4: Rodar e ver passar**

Run: `pytest tests/test_theme.py -v`
Esperado: 7 passed

- [ ] **Step 5: Implementar `ui/widgets.py`**

```python
import pygame

from ui.theme import Theme


class TextCache:
    """Cache de superficies de texto.

    `font.render()` e a operacao mais cara do frame em 1080x1920. Sem este
    cache, 60 FPS nao se sustentam.
    """

    def __init__(self, limite: int = 512):
        self._cache: dict[tuple, pygame.Surface] = {}
        self._limite = limite

    def render(self, font: pygame.font.Font, texto: str, cor: tuple) -> pygame.Surface:
        chave = (id(font), texto, cor)
        achado = self._cache.get(chave)
        if achado is not None:
            return achado

        if len(self._cache) >= self._limite:
            self._cache.clear()

        superficie = font.render(texto, True, cor)
        self._cache[chave] = superficie
        return superficie

    def limpar(self) -> None:
        self._cache.clear()


class Draw:
    """Primitivas de desenho, todas em unidades logicas."""

    def __init__(self, surface: pygame.Surface, theme: Theme, texto: TextCache):
        self.surface = surface
        self.theme = theme
        self.texto = texto
        self.s = theme.scale

    def _px(self, valor: float) -> int:
        return int(valor * self.s)

    def rect(self, r, cor, raio: float = 0) -> None:
        pygame.draw.rect(self.surface, cor, r.to_px(self.s), border_radius=self._px(raio))

    def panel(self, r, cor=None, raio: float = 24) -> None:
        self.rect(r, cor or self.theme.cores["painel"], raio)

    def barra(self, r, valor: float, maximo: float, cor) -> None:
        self.rect(r, self.theme.cores["painel_claro"], r.h / 2)
        if maximo <= 0:
            return
        razao = max(0.0, min(1.0, valor / maximo))
        if razao <= 0:
            return
        from ui.theme import Rect

        self.rect(Rect(r.x, r.y, r.w * razao, r.h), cor, r.h / 2)

    def texto_em(
        self,
        texto: str,
        x: float,
        y: float,
        fonte: pygame.font.Font,
        cor=None,
        centralizado_em: float | None = None,
    ) -> None:
        superficie = self.texto.render(fonte, texto, cor or self.theme.cores["texto"])
        if centralizado_em is not None:
            x = centralizado_em - superficie.get_width() / (2 * self.s)
        self.surface.blit(superficie, (self._px(x), self._px(y)))

    def circulo(self, x: float, y: float, raio: float, cor) -> None:
        pygame.draw.circle(self.surface, cor, (self._px(x), self._px(y)), self._px(raio))
```

- [ ] **Step 6: Commitar**

```bash
git add ui/theme.py ui/widgets.py tests/test_theme.py
git commit -m "Adiciona tema com layout vertical e cache de texto"
```

---

### Task 15: `ui/hud.py`, `ui/feed.py`, `ui/overlay.py`, `ui/arena.py`

**Files:**
- Create: `ui/hud.py`, `ui/feed.py`, `ui/overlay.py`, `ui/arena.py`
- Test: `tests/test_feed_format.py`

**Interfaces:**
- Consumes: `ui.theme.Theme`, `ui.widgets.{Draw, TextCache}`, `game.state.GameState`, `adapters.base.AdapterStatus`
- Produces: `formatar_anuncio(ann) -> tuple[str, str]` (puro, testável); `Hud.draw(draw, state, status, fila)`; `Feed.draw(draw, state)`; `Overlay.draw(draw, state)`; `Arena.draw(draw, state)`

**Contexto:** a formatação do feed sai em função pura para poder ser testada sem abrir janela.

- [ ] **Step 1: Escrever o teste que falha**

```python
from game.effects import Announcement
from ui.feed import formatar_anuncio


def test_anuncio_de_presente_tem_icone_e_autor():
    a = Announcement(kind="gift", actor="João", text="mandou Rose", detail="+5 XP")
    icone, linha = formatar_anuncio(a)
    assert icone
    assert "João" in linha


def test_anuncio_nunca_mostra_none():
    a = Announcement(kind="gift", actor="", text="", detail="")
    _, linha = formatar_anuncio(a)
    assert "None" not in linha


def test_anuncio_de_follow_usa_o_icone_certo():
    icone, _ = formatar_anuncio(Announcement(kind="follow", actor="Carlos", text="seguiu"))
    assert icone != formatar_anuncio(Announcement(kind="gift", actor="X", text="y"))[0]


def test_linha_do_feed_e_truncada_para_caber():
    a = Announcement(kind="comment", actor="A" * 60, text="B" * 200)
    _, linha = formatar_anuncio(a, largura_max=40)
    assert len(linha) <= 40


def test_kind_desconhecido_nao_quebra():
    icone, linha = formatar_anuncio(Announcement(kind="zzz", actor="Ana", text="algo"))
    assert icone is not None
    assert linha
```

- [ ] **Step 2: Rodar e ver falhar**

Run: `pytest tests/test_feed_format.py -v`
Esperado: FAIL — `ModuleNotFoundError: No module named 'ui.feed'`

- [ ] **Step 3: Implementar `ui/hud.py`**

```python
from game.state import GameState
from ui.theme import Rect, Theme
from ui.widgets import Draw


class Hud:
    """Topo da tela: HP, XP, nivel e contadores da LIVE."""

    def __init__(self, theme: Theme, fontes: dict):
        self.theme = theme
        self.fontes = fontes

    def draw(self, d: Draw, state: GameState, status, fila: int, xp_necessario: int) -> None:
        r = self.theme.rects["hud"]
        c = self.theme.cores

        d.texto_em("TIKTOK GAME", r.x, r.y, self.fontes["titulo"])

        ao_vivo = "AO VIVO" if status.connected else status.detail.upper()
        cor = c["hp"] if status.connected else c["texto_fraco"]
        d.circulo(r.right - 210, r.y + 22, 12, cor)
        d.texto_em(ao_vivo, r.right - 190, r.y + 6, self.fontes["pequena"], cor)

        linhas = [
            ("HP", state.hp, state.max_hp, c["hp"], f"{state.hp}/{state.max_hp}"),
            ("XP", state.xp, max(1, xp_necessario), c["xp"], f"{state.xp}/{xp_necessario}"),
        ]
        y = r.y + 70
        for rotulo, valor, maximo, cor, texto in linhas:
            d.texto_em(rotulo, r.x, y, self.fontes["media"], cor)
            d.barra(Rect(r.x + 70, y + 6, r.w - 340, 26), valor, maximo, cor)
            d.texto_em(texto, r.right - 250, y, self.fontes["pequena"], c["texto_fraco"])
            y += 52

        d.texto_em(f"NIVEL {state.level}", r.x, y, self.fontes["titulo"], c["amarelo"])

        # Contadores da LIVE, lado a lado.
        y += 62
        itens = [
            ("Presentes", state.total_gifts, c["laranja"]),
            ("Likes", state.total_likes, c["hp"]),
            ("Follows", state.total_followers, c["verde"]),
            ("Shares", state.total_shares, c["ciano"]),
        ]
        coluna = r.w / len(itens)
        for i, (rotulo, valor, cor) in enumerate(itens):
            x = r.x + coluna * i
            d.texto_em(str(valor), x, y, self.fontes["media"], cor)
            d.texto_em(rotulo, x, y + 34, self.fontes["minima"], c["texto_fraco"])

        if fila > 0:
            d.texto_em(f"fila: {fila}", r.x, y + 76, self.fontes["minima"], c["texto_fraco"])
```

- [ ] **Step 4: Implementar `ui/feed.py`**

```python
from game.effects import Announcement
from game.state import GameState
from ui.theme import Theme
from ui.widgets import Draw

ICONES = {
    "gift": "PRESENTE",
    "comment": "COMENTARIO",
    "like": "LIKE",
    "follow": "FOLLOW",
    "share": "SHARE",
    "levelup": "NIVEL",
    "special": "ESPECIAL",
    "boss": "CHEFAO",
    "mega": "MEGA",
    "system": "SISTEMA",
}

ICONES_CURTOS = {
    "gift": "(*)",
    "comment": "(#)",
    "like": "(+)",
    "follow": "(+)",
    "share": "(>)",
    "levelup": "(^)",
    "special": "(!)",
    "boss": "(!)",
    "mega": "(!)",
    "system": "(-)",
}


def formatar_anuncio(ann: Announcement, largura_max: int = 46) -> tuple[str, str]:
    """Converte um anuncio em (icone, linha de texto). Funcao pura."""
    icone = ICONES_CURTOS.get(ann.kind, "(-)")

    partes = []
    if ann.actor:
        partes.append(ann.actor)
    if ann.text:
        partes.append(ann.text)
    if ann.detail:
        partes.append(ann.detail)

    linha = " ".join(partes).strip() or "evento"
    linha = " ".join(linha.split())  # colapsa espacos repetidos

    if len(linha) > largura_max:
        linha = linha[: largura_max - 1].rstrip() + "…"

    return icone, linha


class Feed:
    """Rodape: os eventos mais recentes da LIVE."""

    def __init__(self, theme: Theme, fontes: dict):
        self.theme = theme
        self.fontes = fontes

    def draw(self, d: Draw, state: GameState) -> None:
        r = self.theme.rects["feed"]
        c = self.theme.cores

        d.panel(r)
        d.texto_em("EVENTOS", r.x + 24, r.y + 18, self.fontes["media"], c["texto"])

        anuncios = list(state.announcements.active())
        if not anuncios:
            d.texto_em(
                "Aguardando a LIVE...",
                r.x + 24,
                r.y + 84,
                self.fontes["pequena"],
                c["texto_fraco"],
            )
            return

        y = r.y + 74
        altura_linha = 48
        for ann in anuncios[-self.theme.feed_size :]:
            icone, linha = formatar_anuncio(ann)
            cor = self._cor(ann, c)
            d.texto_em(icone, r.x + 24, y, self.fontes["pequena"], cor)
            d.texto_em(linha, r.x + 110, y, self.fontes["pequena"], c["texto"])
            y += altura_linha

    @staticmethod
    def _cor(ann: Announcement, c: dict):
        return {
            "gift": c["laranja"],
            "comment": c["xp"],
            "like": c["hp"],
            "follow": c["verde"],
            "share": c["ciano"],
            "levelup": c["amarelo"],
            "special": c["roxo"],
            "boss": c["roxo"],
            "mega": c["roxo"],
        }.get(ann.kind, c["texto_fraco"])
```

- [ ] **Step 5: Implementar `ui/overlay.py`**

```python
from game.state import GameState
from ui.theme import Rect, Theme
from ui.widgets import Draw


class Overlay:
    """Banners de tela cheia: LEVEL UP, MEGA EVENTO, EVENTO ESPECIAL."""

    def __init__(self, theme: Theme, fontes: dict):
        self.theme = theme
        self.fontes = fontes

    def draw(self, d: Draw, state: GameState, agora: float) -> None:
        grandes = [a for a in state.announcements.active() if a.big]
        if not grandes:
            return

        # Mostra apenas o mais recente: varios banners empilhados viram sopa.
        ann = grandes[-1]
        alpha = ann.alpha(agora)
        if alpha <= 0:
            return

        arena = self.theme.rects["arena"]
        altura = 220
        r = Rect(arena.x + 40, arena.y + arena.h / 2 - altura / 2, arena.w - 80, altura)

        fundo = self._escurecer(self._cor(ann.kind), 0.25)
        superficie = _superficie_com_alpha(self.theme, r, fundo, alpha)
        if superficie is not None:
            d.surface.blit(superficie, r.to_px(self.theme.scale)[:2])

        centro = r.x + r.w / 2
        d.texto_em(ann.text, 0, r.y + 40, self.fontes["gigante"], self.theme.cores["texto"],
                   centralizado_em=centro)
        if ann.detail:
            d.texto_em(ann.detail, 0, r.y + 140, self.fontes["media"],
                       self.theme.cores["texto"], centralizado_em=centro)

    def _cor(self, kind: str):
        c = self.theme.cores
        return {
            "levelup": c["amarelo"],
            "special": c["roxo"],
            "boss": c["roxo"],
            "mega": c["roxo"],
            "system": c["hp"],
        }.get(kind, c["xp"])

    @staticmethod
    def _escurecer(cor, fator: float):
        return tuple(max(0, min(255, int(v * fator))) for v in cor)


def _superficie_com_alpha(theme: Theme, r: Rect, cor, alpha: float):
    import pygame

    if alpha >= 0.99:
        return None
    largura, altura = int(r.w * theme.scale), int(r.h * theme.scale)
    if largura <= 0 or altura <= 0:
        return None
    superficie = pygame.Surface((largura, altura), pygame.SRCALPHA)
    superficie.fill((*cor, int(255 * alpha)))
    return superficie
```

> O `alpha` controla o desaparecimento suave. Se `alpha >= 0.99` retornamos `None` e o painel é desenhado normalmente por `d.panel`, mantendo o caminho rápido sem superfície alpha.

- [ ] **Step 6: Implementar `ui/arena.py`**

```python
from game.state import GameState
from ui.theme import Rect, Theme
from ui.widgets import Draw


class Arena:
    """O mundo do jogo: chao, personagem, inimigos e chefe."""

    def __init__(self, theme: Theme, fontes: dict):
        self.theme = theme
        self.fontes = fontes

    def draw(self, d: Draw, state: GameState) -> None:
        r = self.theme.rects["arena"]
        c = self.theme.cores

        d.panel(r, c["fundo"], raio=0)

        # Chao
        chao_y = state.character.y + state.character.radius + 18
        d.rect(Rect(r.x, chao_y, r.w, 6), c["chao"], raio=3)

        # Faixa de direcao: mostra para onde o publico esta empurrando.
        self._faixa_de_intencao(d, r, state)

        for inimigo in state.enemies:
            self._inimigo(d, inimigo)
        if state.boss is not None and state.boss.is_alive():
            self._boss(d, r, state)
        self._personagem(d, state)

    def _faixa_de_intencao(self, d: Draw, r: Rect, state: GameState) -> None:
        intencao = getattr(state, "intent_display", 0.0)
        if abs(intencao) < 0.05:
            return
        largura = min(abs(intencao), 1.0) * (r.w / 2 - 40)
        x = r.x + r.w / 2 if intencao > 0 else r.x + r.w / 2 - largura
        d.rect(Rect(x, r.y + 16, largura, 10), self.theme.cores["ciano"], raio=5)

    def _personagem(self, d: Draw, state: GameState) -> None:
        p = state.character
        y = p.y - p.y_offset
        cor = self.theme.cores["personagem"]

        if state.effects.active("mega"):
            cor = self.theme.cores["roxo"]
        elif state.effects.active("rage"):
            cor = self.theme.cores["hp"]

        # Sombra no chao, que encolhe durante o pulo.
        encolhimento = 1.0 - min(0.5, p.y_offset / 300)
        d.circulo(p.x, p.y + p.radius + 14, p.radius * encolhimento, self.theme.cores["chao"])

        d.circulo(p.x, y - p.radius, p.radius, cor)
        d.rect(Rect(p.x - p.radius * 0.8, y - p.radius * 0.3,
                    p.radius * 1.6, p.radius * 1.6), cor, raio=12)

        if state.effects.active("shield"):
            d.circulo(p.x, y - p.radius, p.radius * 1.9, self.theme.cores["ciano"])

        if state.effects.active("run"):
            for i in range(3):
                d.rect(
                    Rect(p.x - p.facing * (60 + i * 26), y - 10 - i * 6, 22, 6),
                    self.theme.cores["texto_fraco"],
                    raio=3,
                )

    def _inimigo(self, d: Draw, inimigo) -> None:
        d.circulo(inimigo.x, inimigo.y, inimigo.radius, self.theme.cores["inimigo"])
        d.rect(
            Rect(inimigo.x - inimigo.radius, inimigo.y + inimigo.radius + 6,
                 inimigo.radius * 2, 8),
            self.theme.cores["painel_claro"],
            raio=4,
        )

    def _boss(self, d: Draw, r: Rect, state: GameState) -> None:
        boss = state.boss
        c = self.theme.cores
        d.circulo(boss.x, boss.y, boss.radius, c["boss"])

        barra = Rect(r.x + 60, r.y + 36, r.w - 120, 26)
        d.barra(barra, boss.hp_fraction(), 1.0, c["hp"])
        d.texto_em("CHEFAO", 0, r.y + 74, self.fontes["media"], c["texto"],
                   centralizado_em=r.x + r.w / 2)
```

- [ ] **Step 7: Rodar e ver passar**

Run: `pytest tests/test_feed_format.py -v`
Esperado: 5 passed

- [ ] **Step 8: Commitar**

```bash
git add ui/hud.py ui/feed.py ui/overlay.py ui/arena.py tests/test_feed_format.py
git commit -m "Adiciona HUD, feed, overlay e arena verticais"
```

---

### Task 16: `ui/pygame_ui.py` — a janela

**Files:**
- Modify: `ui/pygame_ui.py` (reescrita)
- Test: manual (abre janela)

**Interfaces:**
- Consumes: todos os módulos `ui/`, `game.state.GameState`, `adapters.base.AdapterStatus`
- Produces: `PygameUI(config, game)` com `draw(status, queue_size, agora)`, `poll() -> set[str]` (teclas), `close()`

- [ ] **Step 1: Implementar**

```python
import logging

import pygame

from adapters.base import AdapterStatus
from game.state import GameState
from ui.arena import Arena
from ui.feed import Feed
from ui.hud import Hud
from ui.overlay import Overlay
from ui.theme import Theme
from ui.widgets import Draw, TextCache

logger = logging.getLogger(__name__)

TAMANHO_FONTE = {
    "minima": 20,
    "pequena": 26,
    "media": 34,
    "titulo": 46,
    "gigante": 92,
}


class PygameUI:
    """Janela 9:16 pronta para o OBS capturar.

    Nao decide nada sobre o jogo: so le o GameState e desenha.
    """

    def __init__(self, config: dict, game):
        self.game = game
        self.theme = Theme.from_config(config)

        pygame.init()
        pygame.display.set_caption("TikTok LIVE Interactive Game")

        tamanho = self.theme.window_size()
        self.screen = pygame.display.set_mode(tamanho)
        self.texto = TextCache()

        escala_fonte = self.theme.scale
        self.fontes = {
            chave: pygame.font.SysFont(
                "Segoe UI", max(8, int(tamanho_px * escala_fonte)), bold=chave in {"titulo", "gigante"}
            )
            for chave, tamanho_px in TAMANHO_FONTE.items()
        }

        self.draw_ctx = Draw(self.screen, self.theme, self.texto)
        self.hud = Hud(self.theme, self.fontes)
        self.feed = Feed(self.theme, self.fontes)
        self.overlay = Overlay(self.theme, self.fontes)
        self.arena = Arena(self.theme, self.fontes)
        self.background = self.theme.cores["fundo"]

    def poll(self) -> set[str]:
        """Le a fila do pygame. Retorna o conjunto de acoes de teclado."""
        acoes: set[str] = set()
        for evento in pygame.event.get():
            if evento.type == pygame.QUIT:
                acoes.add("quit")
            elif evento.type == pygame.KEYDOWN:
                if evento.key == pygame.K_ESCAPE:
                    acoes.add("quit")
                elif evento.key == pygame.K_F5:
                    acoes.add("teste_comentario")
                elif evento.key == pygame.K_F6:
                    acoes.add("teste_presente")
                elif evento.key == pygame.K_F7:
                    acoes.add("teste_rajada")
        return acoes

    def draw(self, status: AdapterStatus, fila: int, agora: float) -> None:
        state: GameState = self.game.state

        # A arena precisa da intencao para desenhar a faixa de direcao.
        state.intent_display = self.game.intent()

        self.screen.fill(self.background)
        self.hud.draw(
            self.draw_ctx,
            state,
            status,
            fila,
            self.game.xp_para_subir(state.level),
        )
        self.arena.draw(self.draw_ctx, state)
        self.feed.draw(self.draw_ctx, state)
        self.overlay.draw(self.draw_ctx, state, agora)

        pygame.display.flip()

    def close(self) -> None:
        try:
            self.texto.limpar()
        finally:
            pygame.quit()
```

> `state.intent_display` é um atributo dinâmico. Para manter o `GameState` limpo, adicione o campo em `game/state.py`:

```python
    intent_display: float = 0.0
```

- [ ] **Step 2: Verificar que a janela abre e fecha**

```powershell
python -c "
import pygame, time
from game.engine import GameEngine
from ui.pygame_ui import PygameUI
cfg = {'app': {'window_width': 1080, 'window_height': 1920, 'render_scale': 0.4, 'feed_size': 6},
       'game': {'max_hp': 100, 'initial_hp': 100, 'initial_speed': 220},
       'limits': {'max_enemies': 10}}
game = GameEngine(cfg)
ui = PygameUI(cfg, game)
ui.poll()
ui.draw(__import__('adapters.base', fromlist=['AdapterStatus']).AdapterStatus(), 0, 0.0)
time.sleep(0.5)
ui.close()
print('janela OK')
"
```

Esperado: `janela OK` e nenhuma exceção. A janela abre em 432x768 (0.4 de 1080x1920).

- [ ] **Step 3: Commitar**

```bash
git add ui/pygame_ui.py game/state.py
git commit -m "Reescreve a UI do pygame para a janela vertical 9:16"
```

---

### Task 17: `main.py` — CLI e game loop

**Files:**
- Modify: `main.py` (reescrita)
- Test: manual

**Interfaces:**
- Consumes: tudo
- Produces: `main(argv=None) -> int`; `build_adapter(args, queue, config)`; flags `--test`, `--script`, `--burst`, `--config`, `--scale`

- [ ] **Step 1: Implementar**

```python
import argparse
import logging
import queue
import random
import sys
import time

import pygame

from adapters.base import AdapterStatus
from adapters.simulated import SimulatedAdapter, run_burst
from core.config import ConfigError, load_config
from core.event_queue import EventQueue
from core.events import EventType, LiveEvent
from core.logging_setup import EventJournal, setup_logging
from core.ratelimit import RateLimiter
from core.rules import RuleEngine
from game.engine import GameEngine
from ui.pygame_ui import PygameUI

logger = logging.getLogger("main")


def parse_args(argv=None):
    p = argparse.ArgumentParser(
        prog="main.py",
        description="Jogo interativo para LIVE do TikTok, em 9:16, para captura pelo OBS.",
    )
    p.add_argument("--config", default="config.json", help="caminho do config.json")
    p.add_argument(
        "--test",
        action="store_true",
        help="modo teste: nao conecta ao TikTok, aceita eventos digitados",
    )
    p.add_argument("--script", help="no modo teste, reproduz um cenario (demo, caos, presentes)")
    p.add_argument(
        "--burst",
        type=int,
        metavar="N",
        help="no modo teste, envia N eventos aleatorios de uma vez e sai",
    )
    p.add_argument("--scale", type=float, help="sobrepoe app.render_scale do config")
    p.add_argument("--username", help="sobrepoe tiktok.username do config")
    return p.parse_args(argv)


def build_adapter(args, fila: EventQueue, config: dict):
    """Live real ou simulada. Este e o UNICO ponto que troca a fonte de eventos."""
    if args.test or args.script or args.burst:
        return SimulatedAdapter(fila, config, interactive=not args.script and not args.burst)

    from adapters.tiktok_live import TikTokLiveAdapter

    return TikTokLiveAdapter(fila, config)


def rodar_script(nome: str, fila: EventQueue, config: dict) -> None:
    """Cenarios roteirizados do modo teste."""
    agora = time.monotonic()

    if nome == "presentes":
        for presente in ["Rose", "GG", "Finger Heart", "Ice Cream Cone", "Doughnut"]:
            fila.put(LiveEvent(type=EventType.GIFT, username="joao", gift_name=presente))
    elif nome == "caos":
        run_burst(fila, config, count=500)
    else:  # demo
        roteiro = [
            LiveEvent(type=EventType.SYSTEM, text="connected"),
            LiveEvent(type=EventType.COMMENT, username="maria", text="direita"),
            LiveEvent(type=EventType.GIFT, username="joao", gift_name="Rose"),
            LiveEvent(type=EventType.COMMENT, username="pedro", text="corre"),
            LiveEvent(type=EventType.FOLLOW, username="carlos"),
            LiveEvent(type=EventType.GIFT, username="ana", gift_name="GG"),
            LiveEvent(type=EventType.SHARE, username="lucas"),
            LiveEvent(type=EventType.COMMENT, username="bia", text="esquerda"),
            LiveEvent(type=EventType.LIKE, username="ana", like_delta=100, like_total=100),
            LiveEvent(type=EventType.GIFT, username="joao", gift_name="Confetti"),
            LiveEvent(type=EventType.GIFT, username="maria", gift_name="Cap", quantity=5),
            LiveEvent(type=EventType.LIKE, username="bia", like_delta=200, like_total=300),
            LiveEvent(type=EventType.GIFT, username="pedro", gift_name="TikTok"),
            LiveEvent(type=EventType.COMMENT, username="carlos", text="pula"),
            LiveEvent(type=EventType.GIFT, username="lucas", gift_name="Lion"),
        ]
        for i, evento in enumerate(roteiro):
            evento.timestamp = evento.timestamp
            fila.put(evento)
            print(f"  [{i + 1}/{len(roteiro)}] {evento.type} {evento.actor()} {evento.gift_name or evento.text}")
    logger.info("Cenario '%s' carregado (%s eventos na fila).", nome, fila.size())


def main(argv=None) -> int:
    args = parse_args(argv)
    setup_logging("logs")
    journal = EventJournal("logs/events.jsonl")

    try:
        config = load_config(args.config)
    except ConfigError as erro:
        print(f"\nERRO DE CONFIGURACAO:\n  {erro}\n", file=sys.stderr)
        return 2

    if args.scale is not None:
        config["app"]["render_scale"] = args.scale
    if args.username is not None:
        config["tiktok"]["username"] = args.username

    fila = EventQueue(maxsize=config["app"].get("queue_max_size", 5000))
    game = GameEngine(config)
    limiter = RateLimiter(
        action_budget=config.get("limits", {}).get("action_budget", {}),
    )
    regras = RuleEngine(config, game, limiter, on_event=journal.record)

    if args.burst:
        run_burst(fila, config, count=args.burst)

    ui = PygameUI(config, game)
    adaptador = build_adapter(args, fila, config)

    if args.script:
        rodar_script(args.script, fila, config)

    adaptador.start()
    logger.info(
        "Sistema iniciado | modo=%s | resolucao=%sx%s | escala=%s",
        "TESTE" if (args.test or args.script or args.burst) else "LIVE REAL",
        config["app"]["window_width"],
        config["app"]["window_height"],
        config["app"]["render_scale"],
    )

    clock = pygame.time.Clock()
    fps = config["app"].get("fps", 60)
    por_frame = config["app"].get("events_per_frame", 25)
    rodando = True

    try:
        while rodando:
            dt = clock.tick(fps) / 1000.0
            agora = time.monotonic()

            acoes = ui.poll()
            if "quit" in acoes:
                rodando = False
            if "teste_comentario" in acoes:
                fila.put(LiveEvent(type=EventType.COMMENT, username="tecla", text="direita"))
            if "teste_presente" in acoes:
                fila.put(LiveEvent(type=EventType.GIFT, username="tecla", gift_name="Rose"))
            if "teste_rajada" in acoes:
                run_burst(fila, config, count=200)

            for evento in fila.drain(por_frame):
                regras.process(evento)

            game.update(dt)
            ui.draw(adaptador.status, fila.size(), agora)

    except KeyboardInterrupt:
        logger.info("Interrompido pelo teclado.")
    finally:
        adaptador.stop()
        # Drena o que sobrou para o journal nao perder os ultimos eventos.
        for evento in fila.drain(1000):
            journal.record(evento)
        journal.close()
        ui.close()
        logger.info(
            "Encerrado | aceitos=%s | descartados=%s",
            fila.accepted,
            fila.dropped,
        )

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
```

- [ ] **Step 2: Verificar o modo teste com cenário**

```powershell
python main.py --test --script demo --scale 0.3
```

Esperado: imprime as 15 linhas do roteiro, abre a janela, mostra o feed com os eventos. ESC fecha.

- [ ] **Step 3: Verificar o burst**

```powershell
python main.py --test --burst 500 --scale 0.3
```

Esperado: a janela abre com 500 eventos já na fila, **sem travar**, e o log mostra `descartados` se a fila estourar.

- [ ] **Step 4: Verificar a recusa de config inválida**

```powershell
python main.py --test --config config.json
# edite config.json, troque a action de Rose para "corree", rode de novo
```

Esperado: mensagem `ERRO DE CONFIGURACAO: rules.gifts[0] (gift=Rose): acao desconhecida 'corree'...` e código de saída 2.

- [ ] **Step 5: Commitar**

```bash
git add main.py
git commit -m "Adiciona CLI com modo teste, cenarios e rajada"
```

---

### Task 18: `config.json` completo

**Files:**
- Modify: `config.json`
- Test: `tests/test_config_real.py`

**Interfaces:**
- Consumes: `core.config.load_config`
- Produces: config válida com ≥10 presentes cobrindo todos os tipos de ação

- [ ] **Step 1: Escrever o teste que falha**

```python
from pathlib import Path

from core.config import load_config
from game.actions import known_actions

RAIZ = Path(__file__).resolve().parent.parent


def test_config_do_projeto_e_valida():
    cfg = load_config(RAIZ / "config.json")
    assert cfg["app"]["window_width"] == 1080
    assert cfg["app"]["window_height"] == 1920


def test_pelo_menos_dez_presentes():
    cfg = load_config(RAIZ / "config.json")
    assert len(cfg["rules"]["gifts"]) >= 10


def test_todos_os_tipos_de_acao_do_pedido_estao_configurados():
    cfg = load_config(RAIZ / "config.json")
    configuradas = {r["action"] for r in cfg["rules"]["gifts"]}
    exigidas = {
        "xp", "run", "jump", "heal", "speed", "shield",
        "damage", "spawn_enemy", "special", "boss", "mega",
    }
    assert exigidas <= configuradas


def test_toda_acao_configurada_existe_no_registro():
    cfg = load_config(RAIZ / "config.json")
    for secao in ("gifts", "comments", "likes", "follows", "shares"):
        for regra in cfg["rules"].get(secao, []):
            assert regra["action"] in known_actions(), f"{secao}: {regra}"


def test_presentes_de_exemplo_do_pedido_estao_presentes():
    cfg = load_config(RAIZ / "config.json")
    nomes = {r.get("gift") for r in cfg["rules"]["gifts"]}
    assert {"Rose", "Heart Me", "GG"} <= nomes


def test_comandos_de_comentario_do_pedido_existem():
    cfg = load_config(RAIZ / "config.json")
    termos = {r["contains"] for r in cfg["rules"]["comments"]}
    assert {"corre", "pula", "xp", "direita", "esquerda"} <= termos


def test_likes_tem_milestone_de_100():
    cfg = load_config(RAIZ / "config.json")
    assert any(r["every"] == 100 for r in cfg["rules"]["likes"])


def test_follows_e_shares_dao_xp():
    cfg = load_config(RAIZ / "config.json")
    assert any(r["action"] == "xp" for r in cfg["rules"]["follows"])
    assert any(r["action"] == "xp" for r in cfg["rules"]["shares"])
```

- [ ] **Step 2: Rodar e ver falhar**

Run: `pytest tests/test_config_real.py -v`
Esperado: FAIL — o `config.json` atual não tem `steer`, `special` nem `boss`; e `damage` não está nos presentes.

- [ ] **Step 3: Escrever o `config.json`**

```json
{
  "app": {
    "fps": 60,
    "window_width": 1080,
    "window_height": 1920,
    "render_scale": 1.0,
    "queue_max_size": 5000,
    "events_per_frame": 25,
    "feed_size": 6,
    "announce_ttl": 4.0
  },
  "tiktok": {
    "username": "@SEU_USUARIO",
    "reconnect_seconds": 5,
    "reconnect_max_seconds": 60,
    "fetch_gift_info": true
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
    "intent_friction": 6.0
  },
  "limits": {
    "max_enemies": 40,
    "action_budget": {
      "spawn_enemy": 4.0,
      "boss": 0.5,
      "special": 1.0,
      "mega": 0.5
    }
  },
  "rules": {
    "gifts": [
      {
        "gift": "Rose",
        "gift_id": null,
        "action": "xp",
        "xp": 5,
        "min_quantity": 1,
        "scale_with_quantity": true,
        "max_multiplier": 50,
        "cooldown": 0.2,
        "per_user_cooldown": 0.5
      },
      {
        "gift": "Heart Me",
        "gift_id": null,
        "action": "run",
        "duration": 3,
        "cooldown": 1,
        "per_user_cooldown": 3
      },
      {
        "gift": "GG",
        "gift_id": null,
        "action": "jump",
        "duration": 0.8,
        "cooldown": 0.5,
        "per_user_cooldown": 1
      },
      {
        "gift": "Finger Heart",
        "gift_id": null,
        "action": "xp",
        "xp": 25,
        "cooldown": 0.5,
        "per_user_cooldown": 2
      },
      {
        "gift": "Ice Cream Cone",
        "gift_id": null,
        "action": "heal",
        "amount": 15,
        "scale_with_quantity": true,
        "max_multiplier": 10,
        "cooldown": 1,
        "per_user_cooldown": 2
      },
      {
        "gift": "Doughnut",
        "gift_id": null,
        "action": "speed",
        "amount": 80,
        "duration": 5,
        "cooldown": 2,
        "per_user_cooldown": 5
      },
      {
        "gift": "Perfume",
        "gift_id": null,
        "action": "shield",
        "duration": 5,
        "cooldown": 2,
        "per_user_cooldown": 6
      },
      {
        "gift": "Cap",
        "gift_id": null,
        "action": "spawn_enemy",
        "amount": 1,
        "scale_with_quantity": true,
        "max_multiplier": 8,
        "min_quantity": 1,
        "cooldown": 1,
        "per_user_cooldown": 3
      },
      {
        "gift": "Confetti",
        "gift_id": null,
        "action": "damage",
        "amount": 20,
        "cooldown": 2,
        "per_user_cooldown": 6
      },
      {
        "gift": "Hand Hearts",
        "gift_id": null,
        "action": "rage",
        "duration": 8,
        "cooldown": 3,
        "per_user_cooldown": 10
      },
      {
        "gift": "Corgi",
        "gift_id": null,
        "action": "special",
        "duration": 5,
        "min_quantity": 5,
        "cooldown": 5,
        "per_user_cooldown": 15
      },
      {
        "gift": "Galaxy",
        "gift_id": null,
        "action": "boss",
        "min_quantity": 1,
        "cooldown": 10,
        "per_user_cooldown": 30
      },
      {
        "gift": "Lion",
        "gift_id": null,
        "action": "mega",
        "duration": 10,
        "xp": 100,
        "cooldown": 10,
        "per_user_cooldown": 30
      }
    ],
    "comments": [
      {
        "contains": "direita",
        "action": "steer",
        "amount": 1,
        "cooldown": 0,
        "per_user_cooldown": 0.4
      },
      {
        "contains": "esquerda",
        "action": "steer",
        "amount": -1,
        "cooldown": 0,
        "per_user_cooldown": 0.4
      },
      {
        "contains": "corre",
        "action": "run",
        "duration": 3,
        "cooldown": 2,
        "per_user_cooldown": 5
      },
      {
        "contains": "pula",
        "action": "jump",
        "duration": 0.8,
        "cooldown": 1,
        "per_user_cooldown": 2
      },
      {
        "contains": "xp",
        "action": "xp",
        "xp": 10,
        "cooldown": 1,
        "per_user_cooldown": 3
      }
    ],
    "likes": [
      {
        "every": 100,
        "action": "xp",
        "xp": 20,
        "cooldown": 0
      },
      {
        "every": 1000,
        "action": "heal",
        "amount": 25,
        "cooldown": 0
      }
    ],
    "follows": [
      {
        "action": "xp",
        "xp": 15,
        "cooldown": 0
      }
    ],
    "shares": [
      {
        "action": "xp",
        "xp": 10,
        "cooldown": 0
      }
    ]
  }
}
```

> Dois presentes usam `damage`: enviar `Confetti` **machuca** o personagem. É um presente de trollagem, o que é intencional e cria tensão — o público tem que decidir se quer isso. Se não quiser, troque a ação de `Confetti` para `heal`.

- [ ] **Step 4: Rodar e ver passar**

Run: `pytest tests/test_config_real.py -v`
Esperado: 8 passed

- [ ] **Step 5: Commitar**

```bash
git add config.json tests/test_config_real.py
git commit -m "Configura 13 presentes, comandos de direcao e milestones de like"
```

---

### Task 19: `README.md`

**Files:**
- Modify: `README.md` (reescrita)

**Interfaces:**
- Consumes: nada (documentação)
- Produces: README que permite instalar, testar, conectar e transmitir sem ajuda externa

- [ ] **Step 1: Escrever o README com estas seções, nesta ordem**

1. **O que é** — um jogo que reage à LIVE, em 9:16, para captura pelo OBS.
2. **⚠️ LEIA ISTO PRIMEIRO: o jogo só aparece para o público se o vídeo sair do PC.** Explicar o limite técnico: câmera virtual do OBS não tem transporte de rede; o app do celular não aceita feed RTMP; compartilhamento de tela espelha a tela do celular. Iniciar a LIVE pelo celular + `python main.py` no PC = o Python recebe os eventos e **o público vê só a câmera do celular**.
3. **Descubra seu caso** — tabela dos três casos (§12.1 da spec) com o teste de diagnóstico. Incluir que a página do producer **redireciona para a home** quando a conta não tem acesso, e que ter LIVE no celular **não implica** ter RTMP.
4. **Instalação no Windows** — venv, `pip install -r requirements.txt`, com o aviso: **não instalar `pygame` junto com `pygame-ce`**; e o plano B de usar Python 3.12/3.13 se o runtime do TikTokLive falhar em 3.14.
5. **Configurar o `config.json`** — username, resolução, e a tabela de todos os campos de uma regra.
6. **Testar sem LIVE** — `--test`, `--test --script demo`, `--test --burst 500`, e a lista de comandos do REPL.
7. **Rodar na LIVE real** — `python main.py`, e o que esperar no log.
8. **CONFIGURANDO OBS PARA O TIKTOK** — instalação; cena; **Settings → Video → Base e Output = 1080x1920**, FPS 30; Settings → Output → CBR 2500–6000 kbps, keyframe 2s; Settings → Stream → Custom + Server URL + Stream Key; adicionar **Window Capture** da janela do jogo; **Transform → Fit to Screen**; as armadilhas (campo de resolução travado → "Ignore streaming service recommendations"; tela preta = canvas horizontal; zonas seguras no topo e na base) e como **verificar** que está certo.
9. **Usar o celular como câmera** — tabela de DroidCam / Iriun / Camo / iVCam com o que funciona no Windows; marcar **EpocCam como descontinuado**; avisar que **scrcpy não é webcam**; e a nota de direção: câmera virtual do OBS empurra o OBS *para dentro* do PC, DroidCam faz o oposto.
10. **Como o público vê o jogo** — o diagrama completo do §26 do pedido, e a latência de 10–30 s explicada em linguagem simples: "quem comenta vê o efeito uns 15 segundos depois; é normal".
11. **Adicionar um presente novo** — exemplo de 3 linhas de JSON, sem tocar em Python.
12. **Adicionar uma ação nova** — escrever uma função com `@register("minha_acao")` em `game/engine.py` e adicionar o campo no `config.json`.
13. **Limitações e honestidade** — TikTokLive é engenharia reversa, não é API oficial, e **a própria biblioteca se declara não pronta para produção**; a assinatura passa por um serviço de terceiros (`api.eulerstream.com`) que já teve quedas; a regra dos **50% de conteúdo gaming** de julho/2025 e por que este projeto está do lado favorecido; **18+** para ir ao vivo; e que o TikTok **não publica** mínimo de seguidores nem lista de países — os números que circulam são observação de comunidade.
14. **Licença** — TikTokLive é AGPL-3.0 modificada, com a exceção §18 que cita "TikTok LIVE games" e **não** exige adotar AGPL. Ressalva: não é parecer jurídico.

- [ ] **Step 2: Verificar todos os comandos do README**

Rodar cada comando PowerShell do README em sequência numa instalação limpa e confirmar que funcionam. Comando que não funciona é comando que não entra.

- [ ] **Step 3: Commitar**

```bash
git add README.md
git commit -m "Reescreve o README com OBS, diagnostico de transmissao e limitacoes"
```

---

### Task 20: Verificação final

**Files:**
- Nenhum arquivo novo

- [ ] **Step 1: Suíte completa**

```powershell
pytest -v
```

Esperado: todos passam, nenhum skip inesperado.

- [ ] **Step 2: Percurso do modo teste**

```powershell
python main.py --test --scale 0.3
```

Digitar, em ordem: `direita`, `direita`, `corre`, `Rose 10`, `GG`, `follow`, `share`, `like 100`, `like 250`, `Lion`, `Galaxy`, `help`, `quit`.

Confirmar: o personagem se move para a direita e desacelera sozinho; `Rose 10` dá 50 XP; `like 250` dispara os milestones 100 e 200; `Lion` mostra o banner MEGA EVENTO; `Galaxy` cria o chefe com barra de HP.

- [ ] **Step 3: Rajada**

```powershell
python main.py --test --burst 2000 --scale 0.3
```

Esperado: a janela abre e permanece responsiva; `logs/app.log` registra os descartes; o FPS não despenca.

- [ ] **Step 4: Queda de rede**

Com `python main.py` rodando contra uma LIVE real, desligar o Wi-Fi por 20 s e religar.

Esperado: o jogo continua rodando, o log mostra `Falha na conexao ... Tentando em Xs`, e a reconexão acontece com backoff crescente. **Nenhum `RuntimeError` no log.**

- [ ] **Step 5: Encerramento limpo**

Fechar com ESC.

Esperado: log com `Encerrado | aceitos=N | descartados=M`; sem thread pendurada; sem exceção no console.

- [ ] **Step 6: Captura no OBS**

Cena 1080x1920 → Window Capture da janela do jogo → Transform → Fit to Screen. Confirmar que o HUD e o feed não ficam sob a legenda do TikTok.

- [ ] **Step 7: Commit final e tag**

```bash
git add -A
git commit -m "Conclui o jogo interativo vertical para LIVE do TikTok"
git tag v1.0.0
```
