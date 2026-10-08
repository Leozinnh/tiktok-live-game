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
| **B — TikTok Live Studio** | Baixe em `tiktok.com/studio/download` (Windows) | ✅ Sim — **seção 7**, e o OBS é dispensável |
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
| `app.render_scale` | Tamanho da janela na sua tela. Vem em **`0.6`** = 648x1152, que cabe num monitor 1080p. `1.0` = 1080x1920 (só em tela 4K); `0.5` = 540x960. **Isto não muda a resolução do jogo** — o OBS captura a janela e escala de volta para 1080x1920 |
| `app.fps` | 60 por padrão. `30` economiza CPU |
| `app.feed_size` | Quantas linhas o painel de eventos mostra. Se não couberem todas, o feed mostra as que cabem em vez de vazar da faixa |
| `app.hud_height` | Altura da faixa do HUD, em pixels lógicos. A arena começa aqui |
| `app.feed_height` | Altura da faixa do feed, no rodapé |
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
Testado aqui: `--burst 9000` (quase o dobro da fila de 5000) roda e mostra `aceitos=9000 |
descartados=4000`, sem travar em momento nenhum.

**`--burst` e `--script` não fecham sozinhos:** eles jogam os eventos e deixam a janela aberta
para você ver o resultado. A contagem final (`aceitos` / `descartados`) aparece no console
quando você aperta **ESC**.

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

## 6. CONFIGURANDO O OBS PARA O TIKTOK (caso A)

> **Você tem o TikTok LIVE Studio?** Então pule para a seção 7 — ele substitui o OBS por inteiro,
> e nada daqui é necessário.

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

## 7. TikTok LIVE Studio (o caminho do caso B)

**Se você tem o LIVE Studio instalado, ignore a seção 6 inteira.** Ele substitui o OBS: é o app da
própria TikTok, faz a captura e envia para a LIVE sem Server URL e sem Stream Key. Não instale o OBS
também — dois programas disputando a mesma janela só cria confusão.

Também **não precisa da seção 8** (celular como câmera): o vídeo sai inteiro do PC.

### 7.1 Antes de abrir o LIVE Studio

1. `config.json` → `tiktok.username` precisa ter o seu @ de verdade (não o `@SEU_USUARIO`).
2. Rode o jogo **primeiro**:

```
.venv\Scripts\python.exe main.py
```

A janela se chama **`TikTok LIVE Interactive Game`**. É por esse nome que você vai achá-la na
captura — deixe-a aberta e **visível**.

### 7.2 Criar o palco em 9:16

Escolha o modo **Portrait / retrato (9:16)**, não Dual nem Landscape. A resolução de retrato padrão
é **1080x1920** — exatamente a proporção da janela do jogo.

> Palco e fonte com proporções diferentes = **tarja preta**. Aqui os dois são 9:16, então a janela
> do jogo preenche o palco inteiro sem tarja.

### 7.3 Adicionar a janela do jogo

1. **Add Source** (o "+") → **Window Capture**.
2. Na lista de janelas, escolha **`TikTok LIVE Interactive Game`**.
3. Estique a fonte até cobrir o palco inteiro (ou use o ajuste automático de enquadramento, se
   houver).

Se aparecer **Game Capture** ("Capture specific window"), ele costuma dar imagem melhor para
conteúdo de jogo — mas se ficar **preto**, apague a fonte e volte para **Window Capture**.

### 7.4 Tela preta: a lista de suspeitos

| Sintoma | Causa provável e solução |
|---|---|
| Fonte preta no palco | Rode o **LIVE Studio como administrador** (botão direito no ícone → Executar como administrador). É a causa mais comum |
| Continua preta | O jogo está **minimizado** ou atrás de outra janela. Traga-o para a frente |
| Continua preta | Apague a fonte e refaça com **Window Capture** em vez de Game Capture |
| O jogo aparece, mas o cursor some | Desmarque **Capture Cursor** nas propriedades da fonte |
| Quadro travado em 5–10 fps | Feche outros apps que também estejam sendo capturados; o jogo em si é leve |

### 7.5 Nitidez: o `render_scale` na sua tela

O jogo roda em `render_scale = 0.6` — janela de **648x1152**, que o LIVE Studio estica para
1080x1920. É um aumento de 1,67x: fica bom, mas levemente macio.

Sua tela é **3440x1440**, então cabe mais. Com `render_scale: 0.72` a janela fica **778x1382**
(ainda cabe nos 1440 de altura com a barra de título), o esticão cai para 1,39x e o texto sai mais
nítido. Teste os dois e fique com o que agradar: **a proporção continua 9:16**, então nada mais
precisa ser reajustado.

### 7.6 Antes de ir ao ar

1. Confirme que a janela do jogo está na frente, com o HUD inteiro visível.
2. Rode `--test` (seção 4) e confirme que o presente aparece **no palco do LIVE Studio** — ainda
   sem estar ao vivo.
3. Só então inicie a LIVE.

> **Honestidade sobre esta seção:** os *princípios* aqui são verificados — 9:16 capturando 9:16
> não gera tarja, e uma janela capturada por outro programa precisa estar visível e não minimizada.
> Os **nomes de menu** do LIVE Studio vêm de guias da comunidade, não de documentação oficial: a
> TikTok não publica manual do LIVE Studio. Um rótulo pode estar com nome um pouco diferente na sua
> versão. A seção 14 registra isso.

---

## 8. Usar o celular como câmera

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

## 9. Como o público vê o jogo

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

## 10. O renderer 3D (o visual novo)

O jogo tem **dois renderers**, e os dois leem o mesmo `GameState`. Nada da lógica — regras,
níveis, presentes, anti-spam — sabe qual dos dois está desenhando.

| | `pygame` (padrão) | `3D no navegador` |
|---|---|---|
| Comando | `python main.py` | `python main.py --web` |
| Onde aparece | janela do pygame | `http://127.0.0.1:8765` no navegador |
| Como o OBS captura | Captura de Janela | **Captura de Navegador** |
| Visual | formas 2D | cena Three.js com luz, sombra e profundidade |

### Como rodar

```powershell
.venv\Scripts\python.exe main.py --web
```

Ele imprime a URL no terminal. **Abra no navegador** (`http://127.0.0.1:8765`), deixe em tela
cheia e aponte o OBS para essa aba. Para trocar a porta: `--web --porta 9000`.

No OBS, a fonte é **Captura de Navegador** (Browser), não Captura de Janela — o resto da
seção 6 vale igual. O palco já é 9:16, então não estique nem corte nada.

### Por que o navegador, e não o pygame

O pygame não desenha luz nem sombra: não existe modelo de iluminação, e sombra teria que ser
desenhada à mão, por forma. O navegador tem WebGL no hardware, e o Three.js entrega
iluminação, sombra projetada e profundidade de graça. O custo é uma peça a mais na
arquitetura — o que **não** mudou a arquitetura, só a ponta dela:

```
GameEngine ──► GameState ──┬──► ui/ (pygame)          ──► janela  ──► OBS
                           │
                           └──► renderer_web/snapshot ─► WebSocket ─► Three.js ─► OBS
```

O `main.py --web` **não importa pygame em momento nenhum** — e isso tem teste
(`test_modo_web_nao_carrega_pygame`). Não é firula: importar pygame abre o SDL, então o modo
web exigia ambiente gráfico sem usar nenhum. As duas pontas são independentes: se um dia
houver um renderer Unity ou Godot, ele consome o mesmo `GameState.to_dict()`.

### Como a taxa de quadros não depende da internet

O laço do jogo **nunca escreve no soquete**. Ele chama `publicar()`, que só guarda o retrato
mais recente debaixo de um cadeado; uma thread separada acorda 20 vezes por segundo e é quem
escreve para os navegadores. Um celular em 3G que não consegue acompanhar perde quadros e
nada mais — o jogo no PC segue liso. Há um teste para isso
(`test_publicar_nao_espera_cliente`), porque é o tipo de coisa que só se percebe quando a
LIVE já está no ar e travando.

### O que dá e o que não dá para conferir sem navegador

Duas coisas são geometria pura e foram conferidas rodando o **Three.js de verdade** no Node —
inclusive as duas mais traiçoeiras:

- **A névoa.** Com um `Fog` de alcance fixo, a câmera ficava a 19 unidades e a nevoa
  começava a 16: a arena inteira aparecia lavada, justamente no fundo da tela, que é de onde
  os inimigos vêm. Agora o alcance é **calculado a partir da posição da câmera** e recalculado
  a cada redimensionamento.
- **O enquadramento.** O que a câmera tem de enquadrar **não é a arena, é tudo que pode
  aparecer nela**: as quatro quinas e o personagem encostado nas duas paredes, do pé à
  cabeça. Enquadrar só as quinas deixava a cabeça dele sair pela borda direita
  (`ndc.x = 1,006`) — e o defeito só aparecia depois que alguém mandava o boneco para lá, ao
  vivo. A lista vive em `pontosObrigatorios()`, e é ela que o teste usa.

Rode você mesmo, sem abrir nada:

```
node .superpowers/sdd/<plano>/verifica_camera.mjs
```

O resto — iluminação, sombras, animações — só se vê abrindo a página. A imagem foi conferida
com **Chrome em modo headless** (`--screenshot`), que é como os defeitos de enquadramento
foram encontrados; a seção 14 lista o que continua sem conferência.

### Ajustar a câmera

Tudo fica em `web/camera.js`, com os números medidos em comentário:

| Constante | O que faz |
|---|---|
| `INCLINACAO` | ângulo da câmera, em graus, medido do chão. `45` é o padrão |
| `CAMPO_DE_VISAO` | abertura da lente. Estreita (`26`) de propósito — ver abaixo |
| `ALTURA_ALVO` | altura do ponto que a câmera olha |
| `SOBRA_CHAO` | quanto de chão existe além do piso — é para onde a névoa se dissolve |
| `PASSEIO` | até onde o personagem vai, contando o corpo dele |

Aos 45° o personagem ocupa ~9,3% da altura do painel e o piso ocupa 56% do quadro. **Não é
chute:** as duas tabelas de medição estão no comentário das constantes — subir a inclinação
enche mais o quadro *e* encolhe o personagem ao mesmo tempo (aos 60° ele vira um risco de
5,6%), e fechar a lente devolve tamanho sem custar quadro nenhum. A câmera fica a ~32
unidades em qualquer um dos casos, porque quem manda na distância é o personagem na parede.

---

## 11. Adicionar um presente novo

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

## 12. Adicionar uma ação nova

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

## 13. Limitações e honestidade

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

## 14. O que foi verificado — e o que não foi

Verificado nesta máquina, rodando os comandos exatamente como estão escritos aqui:

| Verificação | Resultado |
|---|---|
| Suíte de testes (`pytest`) | **229 passaram**, nenhum skip |
| Instalação limpa (`venv` + `pip install -r requirements.txt`) | OK no Python 3.14.6 |
| `python main.py` com o placeholder de username | Recusa com mensagem clara, código de saída 2 |
| `--test --script demo` | 15 eventos, level up, chefe, banners, sai limpo no ESC |
| A sequência de REPL da seção 4 | `Rose 10` = +50 XP · `like 250` = 2 marcos · `Lion` = banner MEGA · `Galaxy` = chefe |
| `--burst 2000` e `--burst 9000` | Sem travar. Com 9000, a fila enche em 5000 e descarta 4000 |
| `--web`: HTTP + WebSocket ponta a ponta | 34 conferências: os arquivos são servidos, travessia de caminho é recusada, e um retrato chega por WebSocket com o personagem dentro |
| Enquadramento da câmera 3D (Three.js real, no Node) | Tudo cabe no quadro — inclusive o personagem nas duas paredes, do pé à cabeça; a névoa não pega no piso; o personagem fica com 9,3% do painel |
| A imagem do renderer 3D (Chrome headless, 1080x1920) | O boneco anda e para na hora certa, os membros articulam no ombro, o piso e a borda marcam a área de jogo, e o personagem com escudo e mega continua dentro do quadro |
| `--web`, fechar com conexão pendurada | Fecha em ~1 s, não em 10 s |
| `--web` num ambiente sem tela | Roda: pygame não é importado neste modo |

**Isto não foi verificado, porque precisa de você:**

- **A conexão real com o TikTok.** Falta uma LIVE no ar. Tudo que a biblioteca `TikTokLive`
  expõe foi conferido contra a versão instalada (7.0.1), mas o handshake de verdade só
  acontece na sua primeira transmissão.
- **O runtime da conexão no Python 3.14.** Instalar e importar funciona; uma conexão longa,
  não foi testada. É exatamente para isso que existe o plano B do 3.12.
- **A captura no OBS.** As configurações acima são as certas para 1080x1920, mas quem
  confirma é a prévia do OBS.
- **O visual do renderer 3D, no navegador de verdade.** A geometria foi conferida no Node e a
  imagem, por capturas do **Chrome em modo headless** — foi assim que apareceram a cabeça
  saindo do quadro na parede e a caminhada que não parava. O que a captura não julga: o ritmo
  das animações (uma imagem é um instante), a suavidade a 60 quadros por segundo e a
  legibilidade no seu monitor. Abra a página antes da LIVE e ajuste `web/jogo.js` — as cores
  estão todas no objeto `COR`, no topo.
- **O modelo 3D do personagem.** Não existe arte: o boneco é montado com caixas no próprio
  código (`criarPersonagem()`). Não há rig nem esqueleto — braço e perna são grupos com o pivô
  no ombro e no quadril, e giram em bloco a partir do `seno` do tempo. É o suficiente para ler
  como caminhada parada e em movimento, mas não é animação de verdade. Se você tiver um arquivo
  `.glb`, ele pode substituir o boneco sem tocar em mais nada — os únicos números que o resto do
  código usa dele estão em `PASSEIO`, no `camera.js`.
- **O TikTok LIVE Studio.** Não foi instalado nem executado nesta máquina (não é software deste
  repositório). A seção 7 traz os princípios verificados — proporção 9:16 do palco, janela visível
  e não minimizada —, mas os **nomes de menu** vêm de guias da comunidade, porque a TikTok não
  publica manual do LIVE Studio.

Na sua primeira LIVE, acompanhe o `logs/app.log`. O que importa ver:

```
INFO adapters.tiktok_live | CONNECTED | @seu_usuario | room=7xxxxxxxxx
INFO core.rules | ACTION | usuario=... | evento=EventType.GIFT | presente=Rose | acao=xp
```

Se o `ACTION` aparecer a cada presente, está tudo ligado de ponta a ponta.

---

## 15. Licença

`TikTokLive` é distribuída sob **AGPL-3.0 modificada**, mas a licença traz uma **exceção (§18) que
isenta explicitamente** quem integra a biblioteca — e **cita "TikTok LIVE games" pelo nome** como
caso que **não** exige adotar AGPL-3.0. Um jogo local como este está coberto pela exceção.

A exceção **cai (§19)** se o projeto virar serviço comercial hospedado, relay de WebSocket ou API de
scraping oferecida a terceiros sem liberar o código do servidor. Como o escopo aqui é local, não se
aplica.

**Isto não é parecer jurídico.** Se você pretende monetizar de forma agressiva, procure um advogado.
