# TikTok LIVE Interactive Game — Python

Sistema modular para transformar eventos de uma LIVE do TikTok em ações de um jogo.

## Arquitetura

```text
TikTok Webcast
     |
     v
adapters/tiktok_live.py
     |
     v
LiveEvent (formato interno)
     |
     v
core/event_queue.py
     |
     v
core/rules.py
     |
     v
game/engine.py
     |
     +------> ui/pygame_ui.py
     |
     +------> futuro: OBS / Browser / Unity / outro renderer
```

A regra importante é: **o jogo não sabe que TikTok existe**.

## Requisitos

- Python 3.11+ recomendado
- Windows, Linux ou macOS
- Uma conta que esteja fazendo LIVE
- Internet

## Instalação

Windows PowerShell:

```powershell
cd caminho\do\projeto

py -3.11 -m venv .venv
.\.venv\Scripts\Activate.ps1

python -m pip install --upgrade pip
pip install -r requirements.txt
```

Se o PowerShell bloquear a ativação:

```powershell
Set-ExecutionPolicy -Scope Process Bypass
.\.venv\Scripts\Activate.ps1
```

Linux/macOS:

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
pip install -r requirements.txt
```

## Configuração

Abra:

```text
config.json
```

Troque:

```json
"username": "@SEU_USUARIO"
```

por:

```json
"username": "@seu_usuario"
```

Não coloque a URL completa. O adapter aceita `@usuario` ou `usuario`.

## Executar

```bash
python main.py
```

A janela do Pygame abre e outra thread fica conectada à LIVE.

F5 cria um evento local de teste de comentário `"corre"`.

ESC fecha o programa.

## Como cadastrar um presente

Exemplo:

```json
{
  "gift": "Rose",
  "gift_id": null,
  "action": "xp",
  "amount": 1,
  "xp": 5,
  "duration": 0,
  "cooldown": 0.2
}
```

A biblioteca entrega o nome do presente. O nome no config precisa coincidir com o nome recebido pela integração.

Se quiser usar ID, preencha `gift_id` quando o ID real estiver disponível.

## Ações disponíveis

O GameEngine desta versão possui:

- `xp`
- `heal`
- `damage`
- `damage_all`
- `run`
- `jump`
- `speed`
- `shield`
- `rage`
- `mega`
- `spawn_enemy`

Para criar uma ação nova, adicione um novo `elif action == "...":` em:

```text
game/engine.py
```

O TikTok adapter não precisa ser alterado.

## Comentários

Exemplo:

```json
{
  "contains": "corre",
  "action": "run",
  "amount": 1,
  "duration": 3,
  "cooldown": 2
}
```

Qualquer comentário que contenha `corre` dispara a ação.

## Likes

Exemplo:

```json
{
  "every": 100,
  "action": "xp",
  "amount": 1,
  "xp": 20,
  "duration": 0,
  "cooldown": 0
}
```

A regra dispara a cada 100 curtidas acumuladas.

## Streak de presentes

Presentes que possuem streak são tratados pelo adapter para evitar executar a ação repetidamente em cada atualização intermediária.

A implementação usa o `repeat_count`/estado de streak fornecido pelo TikTokLive.

## Logs

Os logs ficam em:

```text
logs/app.log
```

Exemplo:

```text
2026-10-07 23:59:10 | INFO | ... | AÇÃO | usuário=joao | evento=gift | presente=Rose | quantidade=3 | ação=xp
```

## Reconexão

Se o WebSocket cair, o adapter espera o número de segundos configurado em:

```json
"reconnect_seconds": 5
```

e tenta novamente.

## Segurança contra excesso de eventos

Existem três camadas:

1. fila thread-safe;
2. limite de tamanho da fila;
3. limite de eventos processados por frame.

Isso evita que uma rajada de comentários/likes trave o Pygame.

## API oficial x integração não oficial

O projeto usa `TikTokLive`.

Ela é uma biblioteca de terceiros que lê o Webcast interno do TikTok por WebSocket. Ela não é uma API oficial pública do TikTok.

O próprio projeto informa que é reverse engineering e que o protocolo pode mudar.

Para uma aplicação que precise de maior previsibilidade/uptime, a arquitetura permite substituir somente:

```text
adapters/tiktok_live.py
```

por outro adapter, por exemplo um WebSocket gerenciado.

## Evolução recomendada

Depois desta base:

1. criar sprites reais;
2. criar mapa;
3. criar inimigos com IA;
4. adicionar boss;
5. transformar presentes em habilidades;
6. criar ranking por usuário;
7. salvar pontuação em SQLite/PostgreSQL;
8. criar overlay transparente para OBS;
9. adicionar sons;
10. criar painel web para alterar config durante a LIVE;
11. adicionar Redis se houver múltiplos processos;
12. trocar o renderer por browser/Unity sem alterar as regras do jogo.

## Licença

Antes de distribuir comercialmente uma aplicação baseada diretamente em TikTokLive, verifique a licença atual da biblioteca e suas obrigações.
