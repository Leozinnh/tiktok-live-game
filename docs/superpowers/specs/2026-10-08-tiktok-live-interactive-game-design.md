# TikTok LIVE Interactive Game — Design

Data: 2026-10-08
Status: aguardando revisão

## 1. Objetivo

Evoluir o protótipo atual para um jogo que o público **assiste pela LIVE do TikTok** e no qual
ele vê, em tempo real, as próprias ações alterando o jogo. O critério final (§26 do pedido) é
que o espectador sinta que **controla** o jogo através da LIVE — não apenas que manda presentes
e recebe um número de volta.

### 1.1 Critérios de sucesso

Verificáveis, não aspiracionais:

1. Comentários de direção movem o personagem de forma legível com 1–3s de atraso de rede e com
   várias pessoas comandando ao mesmo tempo (sem teleporte).
2. Uma rajada de 500 eventos em um segundo não derruba o FPS nem trava a janela.
3. Um presente novo entra no jogo editando **apenas** `config.json`.
4. `python main.py --test` exercita o jogo inteiro sem LIVE. `python main.py` usa a LIVE real.
   Os dois compartilham fila, regras e jogo.
5. A janela é 9:16 nativo e capturável pelo OBS sem esticar uma cena 16:9.
6. Queda do TikTok não fecha o jogo; a reconexão é automática e visível no log.

### 1.2 Fora de escopo (v1)

Deliberadamente excluído para manter o projeto terminável. Cada item é aditivo depois:

- Áudio e efeitos sonoros
- Banco de dados / ranking persistente por usuário
- Painel web para editar config durante a LIVE
- Renderer web/Unity — a arquitetura fica pronta, mas não é escrito agora
- Sprites/imagens em `assets/` (v1 desenha com primitivas do pygame)

## 2. Fatos verificados e restrições

Tudo abaixo foi **verificado nesta máquina**, não assumido.

| Fato | Consequência no projeto |
|---|---|
| Python da máquina é **3.14.6** (win_amd64) | Define os alvos de wheel |
| `pygame` **não publica wheel para cp314** — `pip install pygame` falha | `requirements.txt` usa **`pygame-ce`**, fork drop-in (`import pygame` idêntico, mesma API) |
| `pygame-ce 2.5.8` **tem** wheel cp314, e o wheel contém o pacote top-level `pygame` | `import pygame` continua idêntico — nenhuma linha de código muda |
| `pygame` e `pygame-ce` **ambos** instalam em `pygame/` | Nunca instalar os dois juntos: um sobrescreve o outro. O README avisa |
| `TikTokLive 7.0.1` instala no 3.14, mas exige sdists (`protobuf3-to-dict`) | Instalação não pode usar `--only-binary=:all:` |
| `TikTokLive` declara suporte até **3.13**; 3.14 **não** é classificado | Instalar funciona (verificado), mas o **runtime** em 3.14 é não verificado — o README traz o plano B (venv com 3.12/3.13) |
| `TikTokLive 7.0.1` puxa `TikTokLiveProto 0.2.2`, `betterproto2`, `protobuf 7.36`, `websockets 17.2`, `pyee 13` | Essas versões ficam fixadas no `requirements.txt` |
| Não havia `.venv`, `logs/`, `assets/` nem repositório git | Criados; git inicializado |
| `ui/pygame_ui.py` é 1280x720 com layout em pixels absolutos | Renderer é **reescrito**, não adaptado |

### 2.1 Restrição de integração

`TikTokLive` consome o **Webcast interno do TikTok** por WebSocket. É engenharia reversa, **não é
API oficial**, e o protocolo pode mudar sem aviso. Isso é declarado no README e é a razão de a
integração estar isolada em `adapters/tiktok_live.py`: se ela quebrar, só esse arquivo muda.

## 3. Arquitetura

### 3.1 Direção de dependência

```
adapters/  ──►  core/  ──►  game/  ──►  ui/
```

Regras invioláveis:

- `game/` **não importa `pygame`** e não conhece TikTok.
- `core/` **não importa `TikTokLive`**.
- `ui/` **só lê** o estado do jogo; nunca escreve nele.

É isso que permite trocar o renderer por navegador, Unity ou Godot sem tocar em TikTok nem nas
regras. `GameState.to_dict()` já sai pronto para um renderer web consumir.

### 3.2 Mapa de módulos

```
main.py                  CLI (--test/--live), monta as peças, game loop

core/
  config.py              carrega, faz merge de defaults e VALIDA o schema
  events.py              LiveEvent + EventType
  event_queue.py         fila thread-safe, política de descarte, estatísticas
  rules.py               RuleEngine: LiveEvent -> ação
  ratelimit.py           cooldowns (regra, usuário) e orçamento global
  logging_setup.py       app.log com rotação + events.jsonl estruturado

adapters/
  base.py                Protocolo LiveAdapter (start/stop/status)
  tiktok_live.py         integração real (TikTokLive)
  simulated.py           modo teste (REPL, script, burst)

game/
  state.py               GameState + contadores (dados puros)
  entities.py            Character, Enemy, Boss
  effects.py             efeitos temporários + fila de anúncios
  actions.py             ACTION_REGISTRY: nome -> função
  engine.py              simulação + despacho de ações

ui/
  theme.py               cores, fontes, medidas (derivadas da resolução)
  widgets.py             TextCache, barra, painel
  hud.py                 topo: HP/XP/level/contadores
  feed.py                rodapé: eventos recentes
  overlay.py             toasts e banners de tela cheia
  arena.py               personagem, inimigos, chão
  pygame_ui.py           janela e orquestração do frame

docs/superpowers/specs/  esta spec
```

`core/ratelimit.py` e `game/actions.py` não estavam no seu §20 — foram separados porque
concentram lógica que, misturada, tornaria `rules.py` e `engine.py` grandes demais.

### 3.3 Fluxo de dados

```
TikTokLive (thread própria, asyncio)
        │  normaliza para LiveEvent
        ▼
EventQueue (thread-safe, limitada, com descarte)
        │  main thread consome N por frame
        ▼
RuleEngine  ──► RateLimiter (4 camadas)
        │  ação + payload resolvido
        ▼
GameEngine ──► GameState (hp, xp, level, enemies, effects, contadores)
        │        └──► fila de anúncios ("João mandou Rose +5 XP")
        ▼
ui/ (lê GameState + anúncios) ──► janela 1080x1920 ──► OBS ──► TikTok
```

**Decisão de design:** os anúncios de overlay (§13) são **dados do jogo**, não da UI. Um renderer
futuro mostra os mesmos avisos sem reimplementar a lógica de "o que merece destaque".

## 4. Modelo de eventos

`LiveEvent` continua sendo o contrato único entre adapter e núcleo. Tipos:
`comment`, `gift`, `like`, `follow`, `share`, `system`.

Campos: `type`, `username`, `display_name`, `text`, `gift_name`, `gift_id`, `quantity`,
`like_delta`, `raw`, `timestamp`.

### 4.1 Normalização — responsabilidade do adapter

O adapter entrega **incrementos**, nunca acumulados. Verificado no fonte do wheel 7.0.1:

- **Likes:** `LikeEvent.count` é o **incremento do evento**; `LikeEvent.total` é o **acumulado da
  sala** (int64). Curtidas são **agrupadas** — um evento não é uma curtida, então `contador += 1`
  está errado. O adapter emite `like_delta = count` e `like_total = total`, e o motor de regras
  usa **`total` como fonte da verdade**, com um `max_visto` que só anda para frente. Isso é
  monotônico, então não acumula deriva como somar deltas acumularia.
  ⚠️ O TikTok **limita eventos de like por usuário** após ~10–20; depois disso `event.user` pode
  vir `None` enquanto `total` continua subindo. O adapter trata `user` como possivelmente nulo.
- **Presentes (streak):** só o evento final emite, com `quantity = repeat_count`. O detalhe
  crítico verificado: `event.streaking` é `False` **tanto** para o evento final de um streak
  **quanto** para todo presente não-streakable — então `streaking` sozinho não distingue os dois.
  É preciso checar também `gift.type == 1` (que é o que `gift.streakable` significa).

O campo `raw` preserva o evento original para depuração, mas **nada fora do adapter o lê** — é o
que impede o formato do TikTok de vazar para o resto do sistema.

### 4.2 Contrato verificado da API (TikTokLive 7.0.1)

Verificado lendo o fonte do wheel e introspecção com o pacote instalado. **Vários espelhos de
documentação na internet estão errados para a 7.0.1** — descrevem `event.from_user`,
`event.user_info` e sete eventos de inscrição que **não existem**. Nada disso será usado.

| Item | Fato verificado |
|---|---|
| Import | **`from TikTokLive import TikTokLiveClient`** é o único caminho que funciona. `from TikTokLive.client import TikTokLiveClient` **falha** (`__init__.py` tem 0 bytes) |
| Registro | `@client.on(EventClass)` **e** `client.add_listener(EventClass, fn)` existem e são ambos atuais; recebem a **classe**, não string |
| `run()` | `run(*, process_connect_events=True, compress_ws_events=True, fetch_room_info=False, fetch_gift_info=False, fetch_live_check=True, room_id=None)` — **não existe `process_initial_data`** |
| Comentário | `event.content` (v3) com `event.comment` como alias de leitura; usuário em `event.user` |
| Presente | `event.repeat_count` (total do streak no evento final), `event.repeat_end`, `event.streaking`, `gift.name` (v3; `gift_name` sobrevive como alias), `gift.type`, `gift.diamond_count` |
| Like | `event.count` (incremento), `event.total` (acumulado da sala) |
| Reconexão | **A biblioteca não tem nenhuma.** Em fim limpo `run()` **retorna**; em queda `run()` **levanta exceção**. E o cliente **não é reutilizável** — é obrigatório criar um cliente novo a cada tentativa |
| Encerramento | `await client.disconnect()` e `await client.close()` são ambos **async**. **Não existe `client.stop()`** |

**Bug encontrado no código atual** (`adapters/tiktok_live.py:197`): o `finally` faz
`await client.close()` **de dentro do loop asyncio em execução**. O `close()` chama
`run_until_complete()` internamente, o que levanta `RuntimeError` num loop já rodando. O correto
é `await client.disconnect()`. O `except Exception: pass` que envolve a chamada é justamente o
que tem escondido esse erro.

Erros que o adapter passa a tratar especificamente, em vez de `except Exception` genérico:
`UserOfflineError` (espera longa, ~30s), `UserNotFoundError` (**não** readicionar),
`WebcastBlockedError`, `SignatureRateLimitError` (respeita `.retry_after`).

## 5. Concorrência

Requisito (§18): a conexão TikTok nunca pode travar o jogo.

- Thread do adapter roda `asyncio` próprio, separada da thread do pygame.
- Comunicação **exclusivamente** pela `EventQueue` (thread-safe). Nenhum estado de jogo é
  compartilhado entre threads — o adapter nunca toca em `GameState`.
- Fila com tamanho máximo. Fila cheia **descarta o evento mais antigo** (num jogo ao vivo o
  evento recente vale mais que o antigo) e incrementa um contador de descarte.
- Limite de eventos processados por frame, para uma rajada não gerar um frame gigante.
- `main.py` fecha na ordem: para o adapter → drena a fila → fecha a janela.

## 6. Motor de regras

### 6.1 Schema de regra

```json
{
  "gift": "Rose",
  "gift_id": null,
  "min_quantity": 1,
  "scale_with_quantity": true,
  "max_multiplier": 10,
  "action": "xp",
  "xp": 5,
  "amount": 1,
  "duration": 0,
  "cooldown": 0.2,
  "per_user_cooldown": 1.0,
  "announce": true
}
```

- `min_quantity` — só dispara a partir de N unidades.
- `scale_with_quantity` — multiplica o efeito pelo `repeat_count`.
- `max_multiplier` — teto do multiplicador. Sem ele, um streak de 500 vira 500 inimigos.

`max_multiplier` não foi pedido, mas é o que impede um único presente de derrubar o jogo.

### 6.2 Validação na inicialização

`core/config.py` passa a validar o schema inteiro: nomes de ação existentes no registro, tipos
corretos, números não-negativos, `gift` ou `gift_id` presente. Um erro **impede o programa de
iniciar** e aponta presente + campo.

Hoje só as chaves de topo são conferidas, então `"action": "corree"` vira um warning no meio da
LIVE. Sem validação, "adicionar presente sem tocar em Python" não é seguro.

### 6.3 Anti-spam (4 camadas)

| Camada | Protege contra |
|---|---|
| `cooldown` da regra | Rajada repetida da mesma regra |
| `per_user_cooldown` | Um usuário monopolizando |
| Orçamento global por ação | Muitos usuários disparando a mesma ação no mesmo instante |
| `max_enemies` no `GameState` | Rede de segurança final: a arena nunca vira parede de inimigos |

### 6.4 Likes idempotentes

Fonte da verdade é o campo **`total`** (acumulado da sala, verificado na §4.2), com um
`max_visto` que nunca regride. Guarda-se o **maior milestone já disparado** por regra e só se
anda para frente.

```
like_total  90 → 350   ⇒  dispara 100, 200, 300
like_total 350 → 350   ⇒  nada
like_total 350 → 1050  ⇒  dispara 400 .. 1000
```

Idempotente por construção, e correto para rajadas que pulam vários milestones de uma vez.

**Correção de bug:** em `core/rules.py` o laço de milestones chama `_run_action`, que aplica o
cooldown da própria regra. Com `cooldown > 0`, o segundo milestone da mesma rajada é descartado
em silêncio. A checagem de milestone passa a ser separada da checagem de cooldown.

### 6.5 Comentários

Casamento por termo contido, normalizado (sem acento, minúsculo) — já existe e funciona. Um
comentário pode disparar **várias** regras diferentes, o que permite `"corre"` e `"direita"`
coexistirem.

## 7. Game engine

### 7.1 Estado

`GameState` sai de dentro de `engine.py` para `game/state.py`: hp, max_hp, xp, level, speed,
enemies, boss, effects, total_gifts, total_likes, total_followers, total_shares. Dados puros,
serializável via `to_dict()`.

### 7.2 Modelo de controle — vetor de intenção

O problema: comentários chegam com 1–3s de atraso. Mover o personagem por comentário individual
faz 50 pessoas dizendo "direita" teleportarem o boneco, e "direita" + "esquerda" o fazem piscar.

Solução:

- Cada comentário de direção **soma** a uma intenção: `-1` esquerda, `+1` direita.
- A intenção **decai** exponencialmente (meia-vida ~0.35s).
- O personagem tem **velocidade e aceleração**; ele se move na direção da intenção resultante.
- Intenções opostas se cancelam → o personagem **hesita**. Isso é legível e divertido.
- Com ninguém comandando, ele **patrulha sozinho** devagar, para a tela nunca ficar parada.

Movimento restrito a **um eixo horizontal + pulo**. Um público só controla de verdade um espaço
de 3 comandos (`esquerda`, `direita`, `pula`); 2D livre viraria ruído.

### 7.3 Entidades

- `Character` — hp, xp, level, velocidade/aceleração, posição, estado de pulo.
- `Enemy` — desce em direção ao personagem, causa dano por contato, tem hp.
- `Boss` — inimigo grande com barra de HP própria, invoca inimigos comuns.

Inimigos surgem do topo e das laterais e convergem para o personagem.

### 7.4 Ações (registro extensível)

`game/actions.py` expõe `ACTION_REGISTRY: dict[str, Callable]`. Adicionar ação = escrever uma
função e registrar uma linha. Sem `elif` gigante.

`xp` · `heal` · `damage` · `run` · `jump` · `speed` · `shield` · `rage` · `spawn_enemy` ·
`special` · `boss` · `mega`

> **Decisão:** "spawnar inimigo" e "spawnar vários inimigos" viram **uma** ação `spawn_enemy`,
> com `amount` decidindo quantos. Dois nomes para a mesma operação só criariam ambiguidade no
> JSON — `{"action": "spawn_enemy", "amount": 5}` já é "vários".

### 7.5 XP e level

Custo crescente e determinístico. O XP necessário para **sair** do nível `L` é:

```
xp_para_subir(L) = xp_per_level + (L - 1) * xp_level_step
```

Com `xp_per_level = 100` e `xp_level_step = 25` (defaults): nível 1→2 custa 100, 2→3 custa 125,
3→4 custa 150. O XP **restante** é carregado para o próximo nível — um presente grande pode
subir vários níveis de uma vez, e o laço processa todos.

Ao subir de nível: aumenta `max_hp` e velocidade, empurra um anúncio `LEVEL UP!` para a fila de
anúncios (com o número do novo nível) e registra no log e no `events.jsonl`.

### 7.6 Efeitos e anúncios

`game/effects.py` guarda:

- **Efeitos temporários** com duração (correr, pular, escudo, fúria, mega) — `running_until` etc.
  Com duração **empilhável** (pega o maior fim, não soma).
- **Fila de anúncios**: cada anúncio tem texto, ícone, gravidade e tempo de vida. A UI só desenha;
  ela não decide o que é importante.

## 8. Apresentação

### 8.1 Layout 1080x1920

```
┌──────────────────────────────┐
│ 🔴 AO VIVO         👥 1.2k   │  HUD topo
├──────────────────────────────┤
│ ❤️ HP   ████████████░░░░  78% │
│ ⭐ XP   ██████░░░░░░░░░░  41% │  barras
│ 🏆 LVL 12          ⚡ 220     │
├──────────────────────────────┤
│      👾         👾           │
│   [toasts flutuantes]        │  ARENA
│              🧍              │
│      👾              👾      │
├──────────────────────────────┤
│ 📢 EVENTOS                   │
│ 🌹 João → Rose         +5 XP │  FEED
│ 💬 Maria → "corre"           │
│ 👍 Ana → Like #300     +20 XP│
└──────────────────────────────┘
```

Banners de tela cheia para `⭐ LEVEL UP!` e `🔥 MEGA EVENTO!`.

### 8.2 Resolução e desempenho

- Resolução **lógica** de projeto: 1080x1920. Toda a matemática de layout usa essas unidades —
  nenhum pixel é escrito à mão no código do layout.
- `render_scale` (padrão `1.0`) multiplica a resolução lógica para obter o tamanho da janela.
  Com o padrão, a janela abre em 1080x1920. Em máquina fraca, `0.6667` abre em 720x1280 —
  **aceitando perda de nitidez**, porque o OBS terá que ampliar de volta para 1080x1920.
  É uma válvula de escape, não o modo recomendado.
- O custo real no pygame é `font.render()` por frame. Um **cache de texto** indexado por
  (texto, fonte, cor) elimina isso. Sem cache, 60 FPS em 1080x1920 não se sustenta.
- `pygame.SCALED` fica desligado: o OBS captura a janela como ela é.

### 8.3 Legibilidade para transmissão

Texto grande, alto contraste, poucos elementos por vez. A tela é assistida em celular, muitas
vezes em qualidade reduzida — o feed mostra os últimos ~6 eventos, não 15.

## 9. Modo teste

```bash
python main.py --test                 # REPL interativo
python main.py --test --script demo   # cenário roteirizado
python main.py --test --burst         # 500 eventos de uma vez
```

REPL aceita `Rose`, `corre`, `GG`, `follow`, `like 100` — e também `gift Rose 10` (quantidade),
`user joao Rose` (usuário específico), `help`, `quit`.

`--burst` existe para **provar** o §19: se o jogo travar com 500 eventos, o anti-spam falhou.

`adapters/simulated.py` implementa o mesmo protocolo `LiveAdapter` e escreve na **mesma fila**.
`main.py` troca uma peça só. Nenhuma lógica é duplicada — é isso que impede teste e produção de
divergirem com o tempo.

## 10. Logs

- `logs/app.log` — formato humano, com **rotação** (uma LIVE longa com spam geraria um arquivo
  enorme; hoje não há rotação).
- `logs/events.jsonl` — estruturado, para o §9/§10 registrarem follow e share com username,
  horário e ação de forma consultável.

Formato do log humano, conforme §17:

```
[09:16:01] GIFT    user=joao gift=Rose quantity=1
[09:16:01] ACTION  xp value=5
[09:16:15] COMMENT user=maria text="corre"
[09:16:15] ACTION  run duration=3
[09:17:40] ERROR   reconectando em 8s (tentativa 3)
```

## 11. Configuração

`config.json` ganha: `app.resolution{width,height,render_scale}`, `app.feed_size`,
`limits{max_enemies, action_budget}` e, por regra, `min_quantity`, `per_user_cooldown`,
`scale_with_quantity`, `max_multiplier`.

Entrega com **≥10 presentes** de exemplo cobrindo todos os tipos de ação do §6: xp, correr,
pular, curar, velocidade, escudo, dano, spawn de inimigo, spawn de vários, evento especial,
boss e mega evento.

Mantém-se a compatibilidade com a config atual: campos ausentes caem em defaults, então a
`config.json` existente não quebra.

## 12. Transmissão e OBS

### 12.0 Nota de confiabilidade das fontes

O Help Center do TikTok (`support.tiktok.com`) é renderizado por JavaScript e **não pôde ser lido
diretamente**; `support.streamyard.com` devolveu HTTP 403. Os textos atribuídos ao TikTok abaixo
vêm de **documentos de política que o próprio TikTok arquivou com procuradorias-gerais de
estados americanos** (relatórios AB 587 da Califórnia, relatório do AG de Nova York) — são
palavras do TikTok sob pena de lei, a fonte oficial mais forte obtida. **Caminhos de menu** vêm
de guias de terceiros, porque o TikTok não os publica. O que não pôde ser confirmado está
marcado **NÃO VERIFICADO**.

TikTok **não publica** número mínimo de seguidores, lista de países atendidos, nem requisitos do
Live Studio. Números que circulam em guias (1.000 vs 10.000 seguidores, testes de 14 vs 180 dias)
**conflitam entre si** e devem ser tratados como observação de comunidade, não como regra.

### 12.1 Os três casos, e como descobrir o seu

O README abre com um teste de diagnóstico, porque o usuário não sabe em qual caso está:

| Caso | Como testar | O jogo chega ao público? |
|---|---|---|
| **A — RTMP próprio** | `tiktok.com` → **Go LIVE** na barra lateral → `livecenter.tiktok.com/producer` → **Server URL** + **Stream Key** aparecem | ✅ Sim, caminho limpo |
| **B — TikTok Live Studio** | Baixar em `tiktok.com/studio/download` (Windows) | ✅ Sim, via Live Studio |
| **C — só celular** | O botão LIVE só existe no app | ❌ **Não. Limite técnico, não política** |

Se a página do producer **redireciona para a home** do Live Center, a conta não tem acesso a
RTMP. Ter LIVE no celular **não implica** ter RTMP — são permissões **separadas**.

### 12.2 O caso C é impossível, e é preciso dizer isso claramente (§25)

Não existe caminho legítimo para o jogo de PC aparecer numa LIVE iniciada pelo **app do celular**:

- A **câmera virtual do OBS não tem transporte de rede**. É um driver de dispositivo registrado
  no Windows, visível apenas para aplicativos **da mesma máquina**. Um celular no mesmo Wi-Fi
  não tem como enxergá-la. **Não há método que faça o app do TikTok aceitar a câmera virtual.**
- O **compartilhamento de tela** do app espelha a tela **do celular**, nunca a do PC.
- O app **não aceita feed RTMP** — RTMP é entrada para os servidores do TikTok, não uma fonte que
  o app possa assinar.

Portanto: **iniciar a LIVE pelo celular e rodar `python main.py` no PC faz o Python receber os
comentários, mas o público vê apenas a câmera do celular.** O jogo roda, invisível. Para o
público ver, o vídeo tem que **sair do PC**. As únicas rotas: (a) OBS/Live Studio no PC com
acesso RTMP, (b) TikTok Live Studio direto, ou (c) emulador Android (BlueStacks) — que é uma rota
de PC disfarçada de celular e ainda exige elegibilidade de LIVE no app.

### 12.3 Regra dos 50% de conteúdo gaming (importante e recente)

Desde **7 de julho de 2025**, o TikTok exige que criadores transmitam **pelo menos 50% de conteúdo
de jogos** para **manter o acesso a ferramentas de terceiros** (OBS, Streamlabs, Restream,
StreamYard). Descumprir revoga ou suspende o acesso; reaplicação após 14 dias exige que 50% das
lives do período sejam de jogos — e a proporção precisa ser mantida continuamente.

**Este projeto é conteúdo de jogos, então está do lado favorecido da regra.** É uma vantagem real
de fazer um jogo em vez de um overlay genérico. A regra vem dos help centers do **Streamlabs e do
Restream** (parceiros oficiais do TikTok relayando a política) — forte, mas de segunda mão.

### 12.4 Requisitos de LIVE

- **18+ para ir ao vivo**: é a posição **oficial** do TikTok, em texto arquivado junto a
  procuradorias-gerais: *"You must be 18 years and older to go LIVE"*. Blogueiros que citam
  "16+ em algumas regiões" conflitam com o texto oficial. A idade vem da **data de nascimento
  cadastrada**.
- **Seguidores**: ~1.000 é o limiar mais relatado para o botão LIVE no app, variando por região.
  **Sem número oficial.**
- Conta em boa situação (sem violações ativas), LIVE disponível na região, app atualizado,
  conta **Pessoal ou Criador** (contas Business têm ferramentas de LIVE limitadas).

### 12.5 OBS — configuração vertical

**Settings → Video:**
- Base (Canvas) Resolution: `1080x1920`
- Output (Scaled) Resolution: `1080x1920`
- FPS: `30` (60 é possível, mas consome banda sem ganho real em celular)

**Settings → Output → Streaming:** CBR, `2.500–6.000 Kbps`, keyframe `2s`, áudio `128 Kbps`.

**Settings → Stream:** Service `Custom` → Server URL + Stream Key.

Armadilhas confirmadas:

1. **Campo de resolução travado** — se não aceitar 1080x1920, marcar **"Ignore streaming service
   recommendations"** em Settings → Stream.
2. **Tela preta no TikTok** — quase sempre é canvas em **1920x1080** em vez de 1080x1920.
3. **Fontes existentes desalinham** ao trocar o canvas: **Transform → Fit to Screen** em cada uma.
   Vale usar uma **Scene Collection separada** para TikTok em vez de destruir as cenas horizontais.
4. **Zonas seguras**: manter **topo e base** livres — o TikTok sobrepõe legenda, botões e nome de
   perfil ali. Isso restringe o HUD do nosso layout, e está considerado na §8.1.
5. **Webcam só oferece formato paisagem**: desmarcar "use preset" na fonte de captura de vídeo.

### 12.6 Celular como câmera

Todas instalam um driver de câmera virtual no PC. Todas funcionam no Windows.

| Ferramenta | SO do celular | Observação |
|---|---|---|
| **DroidCam** | Android (principal), iOS existe | Grátis limitado a **640x480**; Pro para 720p/1080p |
| **Iriun Webcam** | iOS + Android | Grátis com marca d'água; pago remove e libera 1080p |
| **Camo** | iOS + Android | Melhor qualidade de imagem; USB ou Wi-Fi; Android USB exige depuração |
| **iVCam** | iOS + Android | Alternativa atual; USB com latência baixa |
| **NDI HX Camera** | iOS | Sem cabo, via rede; exige NDI Tools no PC — **NÃO VERIFICADO** o estado atual |
| ~~**EpocCam**~~ | iOS | ⚠️ **DESCONTINUADO** — delistado da App Store em ~31/03/2025. Não recomendar |
| **scrcpy** | Android | ⚠️ **Não é webcam** — é espelhamento de tela. Só serve via Window Capture, e mostra a *tela* do celular, não a câmera |

**Direção que não pode ser confundida:** a câmera virtual do OBS empurra o OBS *para dentro* de
apps do PC. DroidCam e similares fazem o **oposto** (câmera do celular *para dentro* do OBS).
Não são alternativas entre si — são mãos opostas.

Falhas comuns em todas: firewall, **isolamento de AP** no roteador, e **Bonjour/mDNS** ausente
(é a causa usual de "meu celular não aparece"). Preferir **USB**.

### 12.7 A latência do TikTok muda o design do controle

Fato com consequência direta no §7.2: **o TikTok carrega 10–30 s de latência** entre o jogo
acontecer e o espectador ver.

Somando com os ~1–3 s do comentário, o ciclo completo é: espectador comenta em `T` → o personagem
se move em `T+2s` → **o espectador vê em `T+15s` ou mais**. A causalidade se mantém (ele vê a
própria ação tendo efeito), mas **ninguém consegue fazer controle fino**.

Consequência: a **meia-vida do vetor de intenção não pode ser curta**. Com decaimento de 0,35 s,
o movimento inteiro aconteceria dentro da janela de latência e o espectador veria um piscar
inexplicável. O padrão passa a ser **1,5 s de meia-vida, configurável** — movimento sustentado o
bastante para ser visível depois do atraso. Comandos momentâneos são inúteis aqui; o que funciona
é **intenção que persiste**.

## 13. Riscos

| Risco | Mitigação |
|---|---|
| TikTokLive quebra (engenharia reversa; a própria biblioteca se declara **não pronta para produção**) | Isolado em um arquivo; `--test` permite jogar sem ele |
| **Assinatura depende de serviço de terceiros** — a biblioteca roteia por `api.eulerstream.com`; houve **múltiplas quedas só em setembro/2026** | Log específico para `SignatureRateLimitError`/`SignAPIError`; o jogo continua rodando offline em vez de cair |
| **Python 3.14 não é oficialmente suportado** pela TikTokLive (classificadores vão até 3.13) | Instalação foi verificada nesta máquina; se o runtime falhar, o README aponta criar o venv com 3.12/3.13 |
| Conta sem acesso a RTMP | README cobre os três caminhos com diagnóstico (§12.1) |
| FPS baixo em 1080x1920 | `render_scale`, cache de texto, feed curto |
| Presente mal configurado derruba a LIVE | Validação na inicialização + `max_multiplier` + teto de entidades |
| `pygame-ce` divergir de `pygame` | É drop-in e mais ativo que o original; API usada é a estável |
| **Latência de 10–30 s** faz o público não perceber a própria influência | Intenção com meia-vida longa (§12.7) e anúncios que permanecem na tela tempo suficiente |
| Revogação do acesso a ferramentas de terceiros pela regra dos 50% | O projeto **é** conteúdo de jogos, então está do lado favorecido (§12.3) |

### 13.1 Licença

`TikTokLive` é **AGPL-3.0 modificada**, mas a licença traz uma **exceção (§18) que isenta
explicitamente** quem integra a biblioteca — e **cita "TikTok LIVE games" pelo nome** como caso
que **não** exige adotar AGPL-3.0. Um jogo local como este está coberto pela exceção.

A exceção **cai (§19)** se o projeto virar serviço comercial hospedado, relay WebSocket ou API
de scraping oferecida a terceiros sem liberar o código do servidor. Como o escopo aqui é local,
não se aplica. O README registra isso em uma seção de licença, com a ressalva de que **não é
parecer jurídico**.

## 14. Verificação

### 14.1 Testes automatizados (lógica pura, sem I/O)

`core/` e `game/` não importam `pygame` nem `TikTokLive`, então a lógica central é testável
direto, sem LIVE e sem abrir janela. É onde TDD se aplica de verdade:

- `test_config.py` — config inválida (ação inexistente, tipo errado, número negativo) é rejeitada com mensagem que aponta presente e campo
- `test_rules.py` — casamento de presente por nome e por ID; `min_quantity`; `scale_with_quantity` respeitando `max_multiplier`; cooldown de regra e por usuário
- `test_likes.py` — 90 → 350 dispara exatamente 100, 200, 300; repetir o mesmo total não dispara; total que regride é ignorado
- `test_intent.py` — intenções opostas se cancelam; decaimento; personagem acelera em vez de teleportar
- `test_levels.py` — curva de XP, XP restante carregado, múltiplos níveis num só presente
- `test_queue.py` — fila cheia descarta o mais antigo e conta o descarte corretamente
- `test_ratelimit.py` — rajada de 50 disparos da mesma ação respeita orçamento e teto

### 14.2 Verificação manual

1. `config.json` com erro de propósito → o programa recusa iniciar e diz qual campo.
2. `--test` REPL: `corre`, `pula`, `Rose`, `follow`, `like 100` produzem efeito visível.
3. `--burst`: 500 eventos não travam; descartes aparecem no log.
4. Desligar a rede com o jogo aberto: o jogo continua rodando e o log registra a reconexão.
5. Fechar com ESC: adapter para, fila drena, janela fecha, **sem `RuntimeError` no log** — é a
   verificação direta da correção do `client.close()` da §4.2.
6. Capturar a janela no OBS em cena 1080x1920 e conferir enquadramento e zonas seguras.
7. Gift streak: enviar um presente streakable e confirmar que só o evento final gera ação, com a
   contagem consolidada.
