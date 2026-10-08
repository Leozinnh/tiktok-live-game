# TikTok LIVE Interactive Game

Um jogo que reage à sua LIVE do TikTok. O público comenta e manda presentes; um personagem
responde na tela em tempo real. A janela é **vertical 9:16 (1080x1920)**, feita para ser capturada
pelo OBS e transmitida junto com a sua câmera.

Não é simulação: os eventos vêm da LIVE de verdade, pela biblioteca `TikTokLive`.

---

## ⚠️ LEIA ISTO PRIMEIRO: o jogo só aparece para o público se o vídeo sair do PC

Este é o erro que faz mais gente perder uma tarde inteira:

> **Iniciar a LIVE pelo celular e rodar `python main.py` no PC faz o Python receber os comentários,
> mas o público vê apenas a câmera do celular. O jogo roda, invisível.**

Não é limitação de política nem falta de configuração — é limite técnico:

- **A câmera virtual do OBS não tem transporte de rede.** Ela é um driver registrado no Windows,
  visível só para programas **da mesma máquina**. Um celular no mesmo Wi-Fi não tem como enxergá-la.
  Não existe método que faça o app do TikTok aceitar a câmera virtual do seu PC.
- **O compartilhamento de tela do app espelha a tela do celular**, nunca a do PC.
- **O app não aceita feed RTMP.** RTMP é entrada para os servidores do TikTok — não é uma fonte que
  o app do celular possa assinar.

**Para o público ver o jogo, o vídeo tem que sair do PC.** As únicas rotas são OBS (ou TikTok Live
Studio) no PC com acesso RTMP, ou um emulador Android. A seção seguinte diz como descobrir se você
tem esse acesso.

---

## 1. Descubra seu caso

Faça este teste **antes de tudo**. Ele decide se o projeto serve para você hoje.

| Caso | Como testar | O jogo chega ao público? |
|---|---|---|
| **A — RTMP próprio** | Vá em `tiktok.com` → **Go LIVE** na barra lateral → abra `livecenter.tiktok.com/producer` → aparecem **Server URL** e **Stream Key** | ✅ Sim, caminho limpo |
| **B — TikTok Live Studio** | Baixe em `tiktok.com/studio/download` (Windows) | ✅ Sim, via Live Studio |
| **C — só celular** | O botão LIVE só existe no app | ❌ **Não. Limite técnico, não política** |

Duas armadilhas na hora do diagnóstico:

- Se a página do producer **redirecionar para a home** do Live Center, sua conta **não tem** acesso
  a RTMP.
- **Ter LIVE no celular não implica ter RTMP.** São permissões separadas — muita conta tem uma e
  não a outra.

**No caso C**, o que ainda funciona: rode `python main.py --test` para desenvolver e testar tudo
(regras, presentes, layout, OBS) sem LIVE nenhuma. Quando — e se — o acesso RTMP aparecer, é só
rodar `python main.py` e nada mais muda.

---

## 2. Instalação no Windows

Precisa de **Python 3.10+** — é o que a `TikTokLive` declara (`Requires-Python: >=3.10`, com
suporte oficial até o 3.13). No PowerShell, dentro da pasta do projeto:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
pip install -r requirements.txt
```

> **Nunca instale `pygame` junto com `pygame-ce`.** Os dois instalam o mesmo pacote de import
> (`import pygame`), e a mistura quebra de formas difíceis de diagnosticar. Este projeto usa
> **`pygame-ce`**, que é um substituto direto e mais ativo — o `requirements.txt` já traz o certo.

> Se o Windows bloquear o `Activate.ps1` por política de execução, rode
> `Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass` e ative de novo. Vale só para esta
> janela do PowerShell.

### Se o runtime do TikTok falhar no Python 3.14

A `TikTokLive` declara suporte de **3.10 a 3.13**. A instalação e a importação foram verificadas
no 3.14, mas o runtime da conexão não. Se você vir erros estranhos ao conectar, crie o ambiente
em **3.12 ou 3.13** — as duas versões mais novas que a biblioteca declara suportar:

```powershell
py -0p                # lista as versoes que voce ja tem instaladas
py -3.12 -m venv .venv312
.\.venv312\Scripts\Activate.ps1
pip install -r requirements.txt
```

Se o `py -0p` não mostrar nenhuma versão entre 3.10 e 3.13, instale uma em `python.org/downloads`
antes: o `py -3.12` só funciona depois disso. Nada mais no projeto depende da versão do Python —
não há recurso de 3.11+ no código.

---

## 3. Configurar o `config.json`

O arquivo vem pronto, com 13 presentes. **Você não precisa abrir o Python para nada disso.**

Obrigatório: troque o username.

```json
"tiktok": { "username": "@SEU_USUARIO" }
```

Enquanto o placeholder `@SEU_USUARIO` estiver lá, o **modo LIVE recusa iniciar** com uma mensagem
clara. O **modo teste (`--test`) aceita**, porque não conecta ao TikTok.

O que mais importa:

| Campo | Para que serve |
|---|---|
| `app.window_width` / `window_height` | **1080x1920.** Não mude sem mudar o OBS junto |
| `app.render_scale` | `1.0` = janela cheia; `0.5` = 540x960, para PCs fracos. O OBS captura e escala de volta |
| `app.fps` | 60 por padrão. `30` economiza CPU |
| `app.feed_size` | Quantas linhas o painel de eventos mostra |
| `app.events_per_frame` | Teto de eventos processados por frame. É uma das travas anti-spam |
| `limits.max_enemies` | Teto de inimigos na tela |
| `limits.action_budget` | Teto global por segundo, por ação. Ex.: `"spawn_enemy": 4.0` |

### Campos de uma regra

```json
{
  "gift": "Rose",              // nome do presente, OU "gift_id": "5655"
  "gift_id": null,
  "min_quantity": 1,           // só dispara a partir de N unidades
  "scale_with_quantity": true, // multiplica pelo repeat_count (streak)
  "max_multiplier": 50,        // teto do multiplicador
  "action": "xp",              // precisa existir no registro de ações
  "xp": 5,
  "amount": 1,                 // pode ser negativo: steer usa -1 para a esquerda
  "duration": 0,               // segundos, para ações temporárias
  "cooldown": 0.2,             // segundos entre disparos da MESMA regra
  "per_user_cooldown": 0.5     // segundos entre disparos do MESMO usuário
}
```

**`max_multiplier` é o campo que impede um presente de derrubar o jogo.** Sem ele, um streak de
500 Roses viraria 500 inimigos. O `config.json` entrega ele em todo presente que escala.

Presente mal configurado **não derruba a LIVE**: a validação roda na inicialização e o programa se
recusa a abrir dizendo qual presente e qual campo estão errados.

---

## 4. Testar sem LIVE

O modo teste escreve na **mesma fila** que o modo real. Muda uma peça só — regras, jogo e visual
são exatamente os mesmos. É por isso que testar aqui vale a pena.

```powershell
python main.py --test                  # REPL: você digita os eventos
python main.py --test --script demo    # cenário roteirizado, sem digitar nada
python main.py --test --burst 500      # 500 eventos aleatórios de uma vez
```

Comandos do REPL:

| Digite | O que acontece |
|---|---|
| `Rose` | Presente (o nome precisa existir no `config.json`) |
| `Rose 10` | Presente com quantidade 10 |
| `corre`, `pula`, `direita`, `esquerda` | Comentário |
| `"bom dia"` | Comentário entre aspas, com espaços |
| `follow` / `share` | Novo seguidor / compartilhamento |
| `like 100` | Cem curtidas |
| `user joao Rose` | Manda como outro usuário |
| `auto` | Rajada aleatória |
| `help` / `quit` | Ajuda / sair |

**`--burst` existe para provar o anti-spam.** Se o jogo travar com 500 eventos, o anti-spam falhou.
Testado aqui: `--burst 9000` (quase o dobro da fila de 5000) roda e sai com `aceitos=9000 |
descartados=4000`, sem travar em momento nenhum.

Atalhos na janela: **F5** comenta, **F6** manda um presente, **F7** rajada. **ESC** fecha.

---

## 5. Rodar na LIVE real

```powershell
python main.py
```

O que aparece no log quando dá certo:

```
INFO main | Sistema iniciado | modo=LIVE REAL | resolucao=1080x1920 | escala=1.0
INFO adapters.tiktok_live | Conectando a LIVE @seu_usuario (tentativa 1)
INFO adapters.tiktok_live | CONNECTED | @seu_usuario | room=7xxxxxxxxx
```

Se a conta estiver fora do ar, o log diz e tenta de novo a cada 30 s — **deixe aberto**, ele conecta
sozinho quando você entrar ao vivo. Se o usuário não existir, ele para e diz para corrigir o
`config.json`. Quedas de conexão têm backoff exponencial com jitter, e o cliente é recriado a cada
tentativa.

Para fechar: **ESC** ou `Ctrl+C`. O programa para o adapter, drena a fila para o `logs/events.jsonl`
e fecha a janela.

---

## 6. CONFIGURANDO O OBS PARA O TIKTOK

### 6.1 Instalar

Baixe em `obsproject.com` e instale. O OBS é gratuito e não tem versão paga.

### 6.2 Criar uma cena vertical

Antes de tudo, crie uma **Scene Collection separada** para o TikTok (`Scene Collection → New`).
Assim você não destrói suas cenas horizontais ao trocar o canvas.

### 6.3 Settings → Video

| Campo | Valor |
|---|---|
| Base (Canvas) Resolution | `1080x1920` |
| Output (Scaled) Resolution | `1080x1920` |
| FPS | `30` (60 consome banda sem ganho real no celular) |

### 6.4 Settings → Output → Streaming

- **Rate Control:** CBR
- **Bitrate:** `2500` a `6000` Kbps
- **Keyframe Interval:** `2`
- **Áudio:** `128` Kbps

### 6.5 Settings → Stream

- **Service:** `Custom...`
- **Server:** a **Server URL** que apareceu no seu caso A
- **Stream Key:** a **Stream Key** do mesmo lugar

### 6.6 Capturar a janela do jogo

1. Rode `python main.py` (ou `--test` para ensaiar).
2. No OBS: **+** em Sources → **Window Capture** → escolha a janela **"TikTok LIVE Interactive Game"**.
3. Clique com o botão direito na fonte → **Transform → Fit to Screen**.

### 6.7 Armadilhas (todas confirmadas)

| Sintoma | Causa e solução |
|---|---|
| O campo de resolução não aceita 1080x1920 | Marque **"Ignore streaming service recommendations"** em Settings → Stream |
| **Tela preta** no TikTok | Quase sempre é o canvas em `1920x1080` em vez de `1080x1920` |
| Fontes desalinhadas ao trocar o canvas | **Transform → Fit to Screen** em cada uma. Por isso a Scene Collection separada |
| Webcam só oferece formato paisagem | Desmarque **"use preset"** na fonte de captura de vídeo |
| Legenda/botões do TikTok cobrindo o jogo | O layout deste projeto já deixa **topo e base livres**. Não mova o HUD para cima |

### 6.8 Como verificar que está certo

1. No OBS, a prévia deve estar **alta e estreita**, não larga.
2. Mande um presente no `--test` e confirme que ele aparece na prévia **na mesma hora**.
3. Entre na sua própria LIVE pelo celular e confirme que o jogo está lá — lembrando que você o verá
   com **10 a 30 segundos de atraso**.

---

## 7. Usar o celular como câmera

Todas estas instalam um driver de câmera virtual **no PC**. Todas funcionam no Windows.

| Ferramenta | Celular | Observação |
|---|---|---|
| **DroidCam** | Android (principal), iOS existe | Grátis limitado a 640x480; Pro libera 720p/1080p |
| **Iriun Webcam** | iOS + Android | Grátis com marca d'água; pago remove e libera 1080p |
| **Camo** | iOS + Android | Melhor imagem; USB ou Wi-Fi (Android por USB exige depuração) |
| **iVCam** | iOS + Android | Alternativa atual; USB com latência baixa |
| **NDI HX Camera** | iOS | Sem cabo, pela rede; exige NDI Tools no PC. Estado atual **não verificado** |
| ~~**EpocCam**~~ | iOS | ⚠️ **DESCONTINUADO** — delistado da App Store em ~31/03/2025. Não use |
| **scrcpy** | Android | ⚠️ **Não é webcam.** É espelhamento de tela — só serve via Window Capture, e mostra a *tela* do celular, não a câmera |

> **A direção não pode ser confundida.** A câmera virtual do OBS empurra o OBS *para dentro* de
> outros programas do PC. DroidCam e similares fazem o **oposto**: a câmera do celular *para dentro*
> do OBS. Não são alternativas entre si — são mãos opostas.

**Falhas comuns (todas):** firewall bloqueando, **isolamento de AP** no roteador (cada aparelho
isolado dos outros) e **Bonjour/mDNS** ausente — esta última é a causa usual de "meu celular não
aparece". **Prefira USB.**

---

## 8. Como o público vê o jogo

```
Espectador comenta "direita"
        │
        ▼
TikTok LIVE  ──►  TikTokLive (biblioteca)  ──►  TikTokLiveAdapter
                                                        │  normaliza para LiveEvent
                                                        ▼
                                                  EventQueue (thread-safe, com descarte)
                                                        │  a thread principal consome N por frame
                                                        ▼
                        RuleEngine  ──►  RateLimiter (4 camadas anti-spam)
                                                        │  ação + valores já resolvidos
                                                        ▼
                        GameEngine  ──►  GameState (hp, xp, nível, inimigos, efeitos)
                                                        │        └──► fila de anúncios
                                                        ▼
                        ui/ lê o GameState  ──►  janela 1080x1920
                                                        │
                                                        ▼
                                                       OBS  ──►  TikTok LIVE
```

### A latência de 10–30 segundos, explicada

O TikTok carrega **10 a 30 segundos** de atraso entre o jogo acontecer e o espectador ver.

Somando com os 1–3 s do comentário, o ciclo completo é:

> O espectador comenta em **T** → o personagem se move em **T+2s** → **ele vê em T+15s**.

A causalidade se mantém — ele vê a própria ação tendo efeito —, mas **ninguém consegue fazer
controle fino**. Por isso o controle aqui é **intenção que persiste**, e não comando instantâneo:
cada comentário de direção empurra o personagem, e o empurrão decai com **meia-vida de 1,5 s**
(configurável em `game.intent_half_life`). Com um decaimento curto, o movimento inteiro aconteceria
dentro da janela de latência e o espectador veria um piscar inexplicável.

**Diga isso no chat:** *"quem comenta vê o efeito uns 15 segundos depois; é normal"*. Vale mais que
qualquer ajuste.

---

## 9. Adicionar um presente novo

**Só JSON. Não abra o Python.**

Abra o `config.json`, ache `rules.gifts` e acrescente três linhas:

```json
{ "gift": "Rosas Vermelhas", "action": "heal", "amount": 20, "cooldown": 1, "per_user_cooldown": 3 }
```

Salve e rode de novo. É isso. Se errar o nome da ação, o programa **não abre** e diz exatamente
qual presente e qual campo estão errados — em vez de falhar no meio da LIVE.

Ações disponíveis hoje:

| Ação | O que faz | Campos que ela lê |
|---|---|---|
| `xp` | Dá experiência | `xp` |
| `heal` | Cura | `amount`, `scale_with_quantity`, `max_multiplier` |
| `damage` | Tira vida — se houver chefe, acerta o chefe | `amount` |
| `run` | Efeito de corrida | `duration` |
| `jump` | Pulo | `duration` |
| `speed` | Velocidade extra temporária | `amount`, `duration` |
| `shield` | Escudo | `duration` |
| `rage` | Fúria | `duration` |
| `steer` | Empurra o personagem (`-1` esquerda, `+1` direita) | `amount` |
| `spawn_enemy` | Cria inimigos | `amount`, `scale_with_quantity`, `max_multiplier` |
| `special` | Evento especial | `duration` |
| `boss` | Invoca o chefe | — |
| `mega` | Evento mega | `duration`, `xp` |

---

## 10. Adicionar uma ação nova

Aqui, sim, é Python — mas é uma função só.

Escreva em **`game/actions.py`**:

```python
@register("congelar")
def _acao_congelar(engine: GameEngine, payload: dict, event: LiveEvent) -> None:
    engine.state.effects.activate("congelar", float(payload.get("duration", 3)))
```

O `@register("congelar")` já a habilita no `config.json` — a validação lê o registro de ações de
verdade, então não existe lista para manter em dois lugares.

---

## 11. Limitações e honestidade

- **A `TikTokLive` é engenharia reversa** do protocolo interno do TikTok. Não é API oficial, pode
  quebrar sem aviso — e **a própria biblioteca se declara não pronta para produção**. Por isso ela
  está isolada em um único arquivo (`adapters/tiktok_live.py`) e por isso o `--test` existe: o jogo
  inteiro roda sem ela.
- **A assinatura das conexões passa por um serviço de terceiros** (`api.eulerstream.com`), que já
  teve múltiplas quedas. Se ele cair, a conexão falha — o jogo continua rodando e o log registra a
  reconexão, mas não chegam eventos novos até o serviço voltar.
- **Regra dos 50% de conteúdo gaming** (desde 7 de julho de 2025): o TikTok exige **pelo menos 50%
  de conteúdo de jogos** para manter o acesso a ferramentas de terceiros como o OBS. Descumprir
  suspende o acesso. **Este projeto é conteúdo de jogos, então está do lado favorecido da regra** —
  é uma vantagem real de fazer um jogo em vez de um overlay genérico.
- **18+ para ir ao vivo.** É a posição oficial do TikTok, em texto arquivado junto a
  procuradorias-gerais de estados americanos: *"You must be 18 years and older to go LIVE"*. A idade
  vem da **data de nascimento cadastrada**.
- **O TikTok não publica** número mínimo de seguidores, lista de países atendidos nem requisitos do
  Live Studio. Os números que circulam em guias (~1.000 seguidores para o botão LIVE, testes de 14
  vs 180 dias) **conflitam entre si** e são observação de comunidade, não regra.
- **O caso C não tem solução técnica.** Se o seu diagnóstico deu "só celular", nenhum ajuste neste
  projeto muda isso — e quem disser o contrário está vendendo alguma coisa.

---

## 12. O que foi verificado — e o que não foi

Verificado nesta máquina, rodando os comandos exatamente como estão escritos aqui:

| Verificação | Resultado |
|---|---|
| Suíte de testes (`pytest`) | **186 passaram**, nenhum skip |
| Instalação limpa (`venv` + `pip install -r requirements.txt`) | OK no Python 3.14.6 |
| `python main.py` com o placeholder de username | Recusa com mensagem clara, código de saída 2 |
| `--test --script demo` | 15 eventos, level up, chefe, banners, encerra limpo |
| A sequência de REPL da seção 4 | `Rose 10` = +50 XP · `like 250` = 2 marcos · `Lion` = banner MEGA · `Galaxy` = chefe |
| `--burst 2000` e `--burst 9000` | Sem travar. 9000 descarta 4000 e encerra sozinho |

**Isto não foi verificado, porque precisa de você:**

- **A conexão real com o TikTok.** Falta uma LIVE no ar. Tudo que a biblioteca `TikTokLive`
  expõe foi conferido contra a versão instalada (7.0.1), mas o handshake de verdade só
  acontece na sua primeira transmissão.
- **O runtime da conexão no Python 3.14.** Instalar e importar funciona; uma conexão longa,
  não foi testada. É exatamente para isso que existe o plano B do 3.12.
- **A captura no OBS.** As configurações acima são as certas para 1080x1920, mas quem
  confirma é a prévia do OBS.

Na sua primeira LIVE, acompanhe o `logs/app.log`. O que importa ver:

```
INFO adapters.tiktok_live | CONNECTED | @seu_usuario | room=7xxxxxxxxx
INFO core.rules | ACTION | usuario=... | evento=EventType.GIFT | presente=Rose | acao=xp
```

Se o `ACTION` aparecer a cada presente, está tudo ligado de ponta a ponta.

---

## 13. Licença

`TikTokLive` é distribuída sob **AGPL-3.0 modificada**, mas a licença traz uma **exceção (§18) que
isenta explicitamente** quem integra a biblioteca — e **cita "TikTok LIVE games" pelo nome** como
caso que **não** exige adotar AGPL-3.0. Um jogo local como este está coberto pela exceção.

A exceção **cai (§19)** se o projeto virar serviço comercial hospedado, relay de WebSocket ou API de
scraping oferecida a terceiros sem liberar o código do servidor. Como o escopo aqui é local, não se
aplica.

**Isto não é parecer jurídico.** Se você pretende monetizar de forma agressiva, procure um advogado.
