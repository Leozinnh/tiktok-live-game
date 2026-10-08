/*
  Renderer 3D do jogo, no navegador.

  Nao ha regra de jogo aqui. O Python manda um retrato do estado 20 vezes
  por segundo e este arquivo so desenha o que chegou — nao decide dano, XP
  nem quem morreu. Duas consequencias praticas:

  - Nao existe a possibilidade de o navegador e o Python discordarem,
    porque so um dos dois pensa.
  - Recarregar a pagina no meio da LIVE nao perde nada: o proximo retrato
    ja traz o estado inteiro.

  Ponte: `renderer_web/` no lado Python.
*/

import * as THREE from './vendor/three.module.min.js';
import { CHAO, ESCALA, PISO, criarCamera, enquadrar, jx, jz, nevoaDaCamera } from './camera.js';

// ------------------------------------------------------------------ cores

const COR = {
  fundo: 0x0e1018,
  terreno: 0x161a26,
  chao: 0x3a4052,
  grade: 0x262c3c,
  borda: 0x8092c4,
  personagem: 0xfad658,
  membro: 0xc9971f,
  cabeca: 0xfff2c4,
  inimigo: 0xe85258,
  boss: 0xa834c8,
  hp: 0xe8484e,
  xp: 0x4a98ff,
  escudo: 0x4a98ff,
  mega: 0xb060f6,
};

// ------------------------------------------------------------- cena e luz

const palco = document.getElementById('arena');

const cena = new THREE.Scene();
cena.background = new THREE.Color(COR.fundo);
// A nevoa escurece o fundo da arena: e o que faz o olho ler profundidade
// mesmo sem o inimigo estar se movendo. O alcance sai da posicao da camera
// (ver `nevoaDaCamera`) e e recalculado no redimensionamento — um valor
// fixo nao sobrevive a mudanca de tamanho da tela.
cena.fog = new THREE.Fog(COR.fundo, 24, 48);

const camera = criarCamera(9, 16);

const renderizador = new THREE.WebGLRenderer({
  antialias: true,
  powerPreference: 'high-performance',
});
renderizador.setPixelRatio(Math.min(window.devicePixelRatio, 2));
renderizador.shadowMap.enabled = true;
renderizador.shadowMap.type = THREE.PCFSoftShadowMap;
palco.appendChild(renderizador.domElement);

cena.add(new THREE.HemisphereLight(0x93a4c4, 0x1a1e2a, 1.5));

const sol = new THREE.DirectionalLight(0xfff2d8, 2.4);
sol.position.set(7, 13, 5);
sol.castShadow = true;
sol.shadow.mapSize.set(1024, 1024);
// O volume da sombra precisa cobrir a arena inteira, senao a sombra some
// no canto perto da borda.
const SOMBRA = 13;
Object.assign(sol.shadow.camera, {
  left: -SOMBRA, right: SOMBRA, top: SOMBRA, bottom: -SOMBRA,
  near: 1, far: 45,
});
sol.shadow.bias = -0.0012;
cena.add(sol);

// ------------------------------------------------------------- o chao

/*
  Duas superficies, e a diferenca entre elas e a informacao mais
  importante da tela.

  Antes havia um plano so, do mesmo tom, com a grade repetida ate onde a
  vista alcancava. O resultado era o personagem parado no meio do nada: um
  grid uniforme e infinito nao diz onde o jogo acontece, e o olho nao tem
  como saber se ele esta no centro ou ja saiu pela borda. Agora o piso da
  arena e mais claro e mais alto, com a grade so dentro dele, e em volta
  fica o terreno escuro — que a nevoa come. A fronteira entre os dois e o
  limite do jogo, visivel o tempo todo.
*/

// O terreno e a mesma constante que a nevoa usa para saber onde terminar.
// Se os dois saissem de contas diferentes, a aresta do plano apareceria.
const terreno = new THREE.Mesh(
  new THREE.PlaneGeometry(CHAO.largura, CHAO.profundidade),
  new THREE.MeshStandardMaterial({ color: COR.terreno, roughness: 1, metalness: 0 }),
);
terreno.rotation.x = -Math.PI / 2;
terreno.position.z = CHAO.centroZ;
terreno.receiveShadow = true;
cena.add(terreno);

// O piso. Dois centimetros acima do terreno: o bastante para nao brigar por
// pixel (z-fighting), de menos para o pe do personagem afundar.
const piso = new THREE.Mesh(
  new THREE.PlaneGeometry(PISO.largura, PISO.profundidade),
  new THREE.MeshStandardMaterial({ color: COR.chao, roughness: 0.9, metalness: 0 }),
);
piso.rotation.x = -Math.PI / 2;
piso.position.set(0, 0.02, PISO.centroZ);
piso.receiveShadow = true;
cena.add(piso);

/*
  Grade retangular, feita a mao. O `GridHelper` do Three.js so faz
  quadrados, e o piso nao e quadrado (12,0 x 11,7) — um quadrado do lado
  maior passaria por fora do piso e a grade vazaria para o terreno.
*/
function gradeRetangular(largura, profundidade, passos, cor) {
  const meiaL = largura / 2;
  const meiaP = profundidade / 2;
  const pontos = [];
  for (let i = 0; i <= passos; i++) {
    const x = -meiaL + (largura * i) / passos;
    const z = -meiaP + (profundidade * i) / passos;
    pontos.push(new THREE.Vector3(x, 0, -meiaP), new THREE.Vector3(x, 0, meiaP));
    pontos.push(new THREE.Vector3(-meiaL, 0, z), new THREE.Vector3(meiaL, 0, z));
  }
  return new THREE.LineSegments(
    new THREE.BufferGeometry().setFromPoints(pontos),
    new THREE.LineBasicMaterial({ color: cor, transparent: true, opacity: 0.5 }),
  );
}

// A grade da a referencia de movimento: sem ela, um piso liso nao mostra
// velocidade nenhuma. Uma celula por metro, como antes.
const grade = gradeRetangular(PISO.largura, PISO.profundidade, Math.round(PISO.profundidade), COR.grade);
grade.position.set(0, 0.03, PISO.centroZ);
cena.add(grade);

// A borda, por cima de tudo: e ela que responde "ate onde eu posso ir".
const borda = new THREE.LineLoop(
  new THREE.BufferGeometry().setFromPoints([
    new THREE.Vector3(-PISO.largura / 2, 0, PISO.topo),
    new THREE.Vector3(PISO.largura / 2, 0, PISO.topo),
    new THREE.Vector3(PISO.largura / 2, 0, PISO.base),
    new THREE.Vector3(-PISO.largura / 2, 0, PISO.base),
  ]),
  new THREE.LineBasicMaterial({ color: COR.borda, transparent: true, opacity: 0.7 }),
);
borda.position.y = 0.04;
cena.add(borda);

// ------------------------------------------------------------- enquadre

// O ajuste da camera vive em `camera.js`, para poder ser conferido no
// Node sem navegador. Aqui so recalculamos quando a janela muda.
function redimensionar() {
  const largura = palco.clientWidth;
  const altura = Math.max(1, palco.clientHeight);
  renderizador.setSize(largura, altura, false);
  camera.aspect = largura / altura;
  camera.updateProjectionMatrix();
  enquadrar(camera);

  // A nevoa depende de onde a camera parou: recalculada aqui, nunca fixa.
  const nevoa = nevoaDaCamera(camera);
  cena.fog.near = nevoa.near;
  cena.fog.far = nevoa.far;
}

new ResizeObserver(redimensionar).observe(palco);

// ------------------------------------------------------------- modelos

/*
  Personagem low-poly, montado com caixas.

  Nao ha malha externa de proposito: um modelo riggado e animado exige
  artista ou asset licenciado. Blocos resolvem hoje e o dia em que houver
  um .glb e so trocar `criarPersonagem` por um GLTFLoader — nada mais no
  arquivo depende da forma.
*/
function criarPersonagem() {
  const grupo = new THREE.Group();

  /*
    Tres tons, e nao um so. Com tudo amarelo o personagem virava uma mancha:
    as pecas se encostam (o tronco termina em 1,38 e a cabeca comeca em
    1,40) e nada separava cabeca, tronco e membro na silhueta. De longe, num
    celular, o publico via um retangulo amarelo andando.

    O tronco ficou mais estreito pelo mesmo motivo: com 0,78 de largura ele
    encostava nos bracos, e um vao de 4 cm e o que faz o bracos aparecerem.
    Os bracos NAO se moveram — `PASSEIO.corpo` em camera.js conta com eles
    em +-0,49.
  */
  const tom = (cor) =>
    new THREE.MeshStandardMaterial({ color: cor, roughness: 0.45, metalness: 0.1 });
  const materiais = {
    corpo: tom(COR.personagem),
    cabeca: tom(COR.cabeca),
    membro: tom(COR.membro),
  };

  const peca = (material, w, h, d, x, y, z) => {
    const malha = new THREE.Mesh(new THREE.BoxGeometry(w, h, d), material);
    malha.position.set(x, y, z);
    malha.castShadow = true;
    grupo.add(malha);
    return malha;
  };

  /*
    Braco e perna giram na ARTICULACAO, nao no meio da peca.

    Girar a caixa no proprio centro faz o membro girar como helice: o ombro
    vai para tras enquanto a mao vai para a frente, que e o oposto de
    andar. Com o pivo no ombro, o membro inteiro vai para o mesmo lado —
    e so isso que faz uma caminhada parecer caminhada.

    As medidas nao mudaram: pivo em 1,17 com a caixa pendurada 0,31 abaixo
    poe o braco de novo entre 0,55 e 1,17, exatamente onde estava.
  */
  const membro = (w, h, d, x, ombro) => {
    const pivo = new THREE.Group();
    pivo.position.set(x, ombro, 0);
    const malha = new THREE.Mesh(new THREE.BoxGeometry(w, h, d), mMembro);
    malha.position.y = -h / 2;
    malha.castShadow = true;
    pivo.add(malha);
    grupo.add(pivo);
    return pivo;
  };

  const { corpo: mCorpo, cabeca: mCabeca, membro: mMembro } = materiais;
  const corpo = peca(mCorpo, 0.7, 0.92, 0.52, 0, 0.92, 0);
  const cabeca = peca(mCabeca, 0.54, 0.52, 0.52, 0, 1.7, 0);
  const bracoE = membro(0.2, 0.62, 0.2, -0.49, 1.17);
  const bracoD = membro(0.2, 0.62, 0.2, 0.49, 1.17);
  const pernaE = membro(0.24, 0.52, 0.24, -0.19, 0.46);
  const pernaD = membro(0.24, 0.52, 0.24, 0.19, 0.46);

  // Escudo: esfera translucida, escondida ate o efeito entrar.
  const escudo = new THREE.Mesh(
    new THREE.SphereGeometry(1.15, 20, 14),
    new THREE.MeshBasicMaterial({
      color: COR.escudo, transparent: true, opacity: 0.22, depthWrite: false,
    }),
  );
  escudo.position.y = 0.85;
  escudo.visible = false;
  grupo.add(escudo);

  grupo.userData = { corpo, cabeca, bracoE, bracoD, pernaE, pernaD, escudo, materiais };
  return grupo;
}

/*
  Inimigo e chefe sao desenhados pelo tamanho que o MOTOR diz, e nao por um
  numero escolhido aqui.

  O octaedro tinha 0,42 fixo — 84 unidades de largura — enquanto o motor
  dizia `radius: 22`, ou seja 44, que e o que o renderer do pygame desenha.
  O dobro. Parecia so um exagero de escala ate nove inimigos convergirem:
  com o dobro do tamanho eles se sobrepunham num bloco vermelho unico, e a
  separacao do motor nao tinha como aparecer na tela. O sprite tem que sair
  da mesma medida que a colisao, senao o publico ve uma coisa e o jogo faz
  outra.

  Por isso a geometria nasce com raio 1 e quem manda no tamanho e o
  `scale`, lido do retrato a cada quadro.
*/
const RAIO_UNITARIO = 1;

function criarInimigo() {
  const malha = new THREE.Mesh(
    new THREE.OctahedronGeometry(RAIO_UNITARIO, 0),
    new THREE.MeshStandardMaterial({
      color: COR.inimigo, roughness: 0.4, metalness: 0.2,
      emissive: COR.inimigo, emissiveIntensity: 0.25,
    }),
  );
  malha.castShadow = true;
  return malha;
}

/*
  O raio com que cada corpo foi DESENHADO aqui, em unidades do mundo — o
  numero que esta nas linhas abaixo, nao um escolhido a parte. O tamanho
  final e a razao entre ele e o `radius` que o motor manda, entao mudar
  `Enemy.radius` no Python muda a tela sem tocar no JS.
*/
const RAIO_DESENHADO = { inimigo: RAIO_UNITARIO, boss: 1.25 };

const escalaDe = (raio, desenhado) => (raio / ESCALA) / desenhado;

/** O inimigo flutua, e a altura do flutuar acompanha o tamanho dele. */
const alturaDoVoo = (raio) => raio * 1.4;

function criarBoss() {
  const grupo = new THREE.Group();
  const corpo = new THREE.Mesh(
    new THREE.DodecahedronGeometry(RAIO_DESENHADO.boss, 0),
    new THREE.MeshStandardMaterial({
      color: COR.boss, roughness: 0.35, metalness: 0.3,
      emissive: COR.boss, emissiveIntensity: 0.35,
    }),
  );
  corpo.position.y = 1.4;
  corpo.castShadow = true;
  grupo.add(corpo);

  // Barra de vida: dois planos que sempre encaram a camera. `Sprite` faz
  // esse giro sozinho, sem conta de billboard no laco.
  const fundo = new THREE.Sprite(new THREE.SpriteMaterial({
    color: 0x000000, transparent: true, opacity: 0.6, depthTest: false,
  }));
  fundo.scale.set(2.7, 0.22, 1);
  fundo.position.y = 3.1;
  grupo.add(fundo);

  const frente = new THREE.Sprite(new THREE.SpriteMaterial({
    color: COR.hp, depthTest: false,
  }));
  frente.scale.set(2.6, 0.14, 1);
  frente.position.set(0, 3.1, 0.01);
  grupo.add(frente);

  grupo.userData = { corpo, frente };
  return grupo;
}

// ------------------------------------------------------------- instancias

const personagem = criarPersonagem();
cena.add(personagem);

const poolInimigos = [];
const poolBoss = [];

let boss = null;
let dados = null;          // ultimo retrato recebido
const alvo = new Map();    // malha -> { x, z } desejados

function obterInimigo(indice) {
  while (poolInimigos.length <= indice) {
    const malha = criarInimigo();
    malha.visible = false;
    cena.add(malha);
    poolInimigos.push(malha);
  }
  return poolInimigos[indice];
}

function obterBoss() {
  if (boss === null) {
    boss = criarBoss();
    boss.visible = false;
    cena.add(boss);
    poolBoss.push(boss);
  }
  return boss;
}

/*
  Casa cada inimigo do retrato com uma malha ja na cena pela POSICAO mais
  proxima, nao pelo indice da lista.

  O retrato nao traz identificador, e casar por indice faz o inimigo do
  meio pular para a posicao do vizinho toda vez que alguem morre — o
  desenho treme. Como todos os inimigos sao iguais, o vizinho mais proximo
  e sempre a escolha certa. Sao no maximo 40x40 comparacoes, 20 vezes por
  segundo: irrelevante.
*/
function distribuirInimigos(lista) {
  const usados = new Set();

  lista.forEach((inimigo, indice) => {
    const desejado = { x: jx(inimigo.x), z: jz(inimigo.y) };

    let melhor = null;
    let melhorDistancia = Infinity;
    for (const malha of poolInimigos) {
      if (usados.has(malha)) continue;
      const atual = alvo.get(malha);
      if (atual === undefined) continue;
      const d = (atual.x - desejado.x) ** 2 + (atual.z - desejado.z) ** 2;
      if (d < melhorDistancia) {
        melhorDistancia = d;
        melhor = malha;
      }
    }

    // Nenhuma malha livre serve: e um inimigo novo. Nasce ja na posicao.
    const malha = melhor ?? obterInimigo(indice);

    // O tamanho vem do motor, a cada quadro: o retrato traz o `radius` de
    // cada inimigo. Sem isto o sprite nao bate com a colisao — era o que
    // fazia nove inimigos separados virarem um bloco vermelho so na tela.
    const raioDoMotor = inimigo.radius ?? RAIO_DESENHADO.inimigo * ESCALA;
    const raio = raioDoMotor / ESCALA;
    malha.scale.setScalar(escalaDe(raioDoMotor, RAIO_DESENHADO.inimigo));
    malha.userData.raio = raio;

    if (melhor === null) {
      malha.position.set(desejado.x, alturaDoVoo(raio), desejado.z);
    }
    usados.add(malha);
    alvo.set(malha, desejado);
    malha.visible = true;
  });

  for (const malha of poolInimigos) {
    if (!usados.has(malha)) {
      malha.visible = false;
      alvo.delete(malha);
    }
  }
}

// ---------------------------------------------------------------- rede

const TITULO = document.getElementById('titulo');
const SELO = document.getElementById('selo');
const SELO_TEXTO = document.getElementById('selo-texto');
const AVISO = document.getElementById('aviso');
const BANNERS = document.getElementById('banners');
const FEED = document.getElementById('feed-lista');

const HUD = {
  hp: document.getElementById('barra-hp'),
  xp: document.getElementById('barra-xp'),
  valorHp: document.getElementById('valor-hp'),
  valorXp: document.getElementById('valor-xp'),
  nivel: document.getElementById('nivel'),
  presentes: document.getElementById('presentes'),
  likes: document.getElementById('likes'),
  follows: document.getElementById('follows'),
  shares: document.getElementById('shares'),
};

/*
  Icone e cor por tipo de aviso — os mesmos papeis de ui/feed.py, mas com
  emoji de verdade: o pygame nao tinha glifo e usava marcadores ASCII, o
  navegador tem.
*/
const ESTILO = {
  gift:    { icone: '🎁', cor: 'var(--laranja)' },
  comment: { icone: '💬', cor: 'var(--xp)' },
  like:    { icone: '❤️', cor: 'var(--hp)' },
  follow:  { icone: '⭐', cor: 'var(--verde)' },
  share:   { icone: '🔁', cor: 'var(--ciano)' },
  levelup: { icone: '🆙', cor: 'var(--amarelo)' },
  special: { icone: '✨', cor: 'var(--roxo)' },
  boss:    { icone: '👑', cor: 'var(--roxo)' },
  mega:    { icone: '🔥', cor: 'var(--roxo)' },
  system:  { icone: '•',  cor: 'var(--texto-fraco)' },
};

const padrao = { icone: '•', cor: 'var(--texto-fraco)' };

// Assinaturas do ultimo desenho. Sem elas o DOM seria reconstruido a cada
// retrato e as animacoes de entrada recomecariam 20 vezes por segundo.
let assinaturaFeed = '';
let assinaturaBanners = '';

const escapar = (texto) => String(texto ?? '').replace(/[&<>"]/g,
  (c) => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;' }[c]));

function desenharFeed(anuncios) {
  const assinatura = anuncios.map((a) => `${a.kind}|${a.actor}|${a.text}|${a.detail}`).join('§');
  if (assinatura === assinaturaFeed) return;
  assinaturaFeed = assinatura;

  FEED.innerHTML = anuncios.map((a) => {
    const estilo = ESTILO[a.kind] ?? padrao;
    return `<li>
      <span class="icone">${estilo.icone}</span>
      ${a.actor ? `<span class="autor" style="color:${estilo.cor}">${escapar(a.actor)}</span>` : ''}
      <span class="texto">${escapar(a.text || a.detail)}</span>
      ${a.detail && a.text ? `<span class="detalhe">${escapar(a.detail)}</span>` : ''}
    </li>`;
  }).join('');
}

function desenharBanners(anuncios) {
  const grandes = anuncios.filter((a) => a.big);
  const assinatura = grandes.map((a) => `${a.kind}|${a.text}|${a.detail}`).join('§');
  if (assinatura === assinaturaBanners) return;
  assinaturaBanners = assinatura;

  BANNERS.innerHTML = grandes.map((a) => {
    const estilo = ESTILO[a.kind] ?? padrao;
    return `<div class="banner" style="color:${estilo.cor}">
      ${escapar(a.text)}
      ${a.detail ? `<span class="detalhe">${escapar(a.detail)}</span>` : ''}
    </div>`;
  }).join('');
}

function desenharHud(d) {
  const fracaoHp = d.max_hp > 0 ? Math.max(0, Math.min(1, d.hp / d.max_hp)) : 0;
  HUD.hp.style.width = `${(fracaoHp * 100).toFixed(1)}%`;
  HUD.valorHp.textContent = `${d.hp} / ${d.max_hp}`;

  // O custo do proximo nivel nao vem no retrato; o Python manda o XP atual
  // e o nivel, e a barra usa o XP do nivel corrente como referencia.
  HUD.xp.style.width = '100%';
  HUD.valorXp.textContent = `${d.xp} XP`;

  HUD.nivel.textContent = d.level;
  HUD.presentes.textContent = d.total_gifts;
  HUD.likes.textContent = d.total_likes;
  HUD.follows.textContent = d.total_followers;
  HUD.shares.textContent = d.total_shares;

  const conectado = d.status?.conectado;
  SELO.className = conectado ? 'ao-vivo' : 'teste';
  const fila = d.status?.fila ?? 0;
  SELO_TEXTO.textContent = conectado
    ? `AO VIVO${fila > 0 ? `  ·  fila ${fila}` : ''}`
    : `TESTE${fila > 0 ? `  ·  fila ${fila}` : ''}`;
}

function aplicar(d) {
  dados = d;
  desenharHud(d);
  desenharFeed(d.announcements ?? []);
  desenharBanners(d.announcements ?? []);
  distribuirInimigos(d.enemies ?? []);

  alvo.set(personagem, { x: jx(d.character.x), z: jz(d.character.y) });

  if (d.boss) {
    const b = obterBoss();
    b.visible = true;
    // Mesma regra do inimigo: o chefe e desenhado no tamanho que o motor
    // diz. O grupo inteiro escala junto — corpo e barra de vida foram
    // montados nas mesmas proporcoes, e escalar so o corpo desalinharia a
    // barra.
    b.scale.setScalar(
      escalaDe(d.boss.radius ?? RAIO_DESENHADO.boss * ESCALA, RAIO_DESENHADO.boss),
    );
    alvo.set(b, { x: jx(d.boss.x), z: jz(d.boss.y) });
    b.userData.fracao = d.boss.max_hp > 0
      ? Math.max(0, Math.min(1, d.boss.hp / d.boss.max_hp))
      : 0;
  } else if (boss !== null) {
    boss.visible = false;
    alvo.delete(boss);
  }
}

function conectar() {
  const protocolo = location.protocol === 'https:' ? 'wss' : 'ws';
  const soquete = new WebSocket(`${protocolo}://${location.host}/ws`);

  soquete.onopen = () => {
    AVISO.hidden = true;
  };

  soquete.onmessage = (evento) => {
    try {
      aplicar(JSON.parse(evento.data));
    } catch (erro) {
      console.error('Retrato invalido', erro);
    }
  };

  soquete.onclose = () => {
    AVISO.hidden = false;
    // O Python pode ter sido reiniciado: tenta de novo sem parar.
    setTimeout(conectar, 1500);
  };

  soquete.onerror = () => soquete.close();
}

// -------------------------------------------------------------- animacao

const relogio = new THREE.Clock();
let tempo = 0;

function animar() {
  requestAnimationFrame(animar);
  const dt = Math.min(relogio.getDelta(), 0.1);
  tempo += dt;

  // Suavizacao exponencial: a 20 retratos por segundo e 60 quadros por
  // segundo, desenhar direto na posicao recebida daria 20 quadros uteis e
  // 40 repetidos. Aqui a malha persegue o alvo e o movimento fica continuo.
  const suavizar = Math.min(1, dt * 16);

  for (const [malha, destino] of alvo) {
    malha.position.x += (destino.x - malha.position.x) * suavizar;
    malha.position.z += (destino.z - malha.position.z) * suavizar;
  }

  if (dados !== null) {
    const d = dados;
    const viva = dados.effects ?? {};

    // --- personagem
    const c = personagem.userData;

    /*
      "Esta andando?" e a distancia que ainda falta percorrer, em unidades
      do MUNDO. Comparar `d.character.x` (unidades do jogo, 0..1080) com
      `personagem.position.x` (mundo, -5,4..5,4) dava sempre verdadeiro: o
      boneco ficava parado batendo as pernas, com a cabeca a 5 unidades de
      distancia do proprio corpo. Estes dois numeros so podem ser
      comparados depois de convertidos — e o destino em `alvo` ja esta
      convertido, porque foi `jx()` quem o escreveu.
    */
    const destinoX = alvo.get(personagem)?.x;
    const andando =
      destinoX !== undefined && Math.abs(destinoX - personagem.position.x) > 0.03;
    const passo = Math.sin(tempo * 11) * (andando ? 0.24 : 0.05);
    c.pernaE.rotation.x = passo;
    c.pernaD.rotation.x = -passo;
    c.bracoE.rotation.x = -passo * 0.7;
    c.bracoD.rotation.x = passo * 0.7;

    // y_offset e o pulo, em unidades do jogo. A respiracao soma aqui, no
    // grupo inteiro: antes ela mexia so o tronco e a cabeca ficava parada
    // no ar, com o pescoco abrindo e fechando.
    personagem.position.y =
      (d.character.y_offset ?? 0) / ESCALA + Math.abs(Math.sin(tempo * 5.5)) * 0.035;

    // facing: -1 encara a esquerda. Vira o grupo inteiro.
    personagem.rotation.y = d.character.facing >= 0 ? 0 : Math.PI;

    c.escudo.visible = 'shield' in viva;
    if (c.escudo.visible) {
      const pulso = 1 + Math.sin(tempo * 6) * 0.04;
      c.escudo.scale.setScalar(pulso);
    }

    // mega: o personagem cresce e passa a brilhar. O brilho vai nos tres
    // tons — acender so um faria a peca mais clara virar a unica visivel.
    const mega = 'mega' in viva;
    for (const material of Object.values(c.materiais)) {
      material.emissive.setHex(mega ? COR.mega : 0x000000);
      material.emissiveIntensity = mega ? 0.6 : 0;
    }
    personagem.scale.setScalar(mega ? 1.35 : 1);

    // --- inimigos
    for (const malha of poolInimigos) {
      if (!malha.visible) continue;
      malha.rotation.y += dt * 2.4;
      const raio = malha.userData.raio ?? RAIO_DESENHADO.inimigo;
      malha.position.y =
        alturaDoVoo(raio) + Math.sin(tempo * 3 + malha.position.x) * raio * 0.4;
    }

    // --- chefe
    if (boss !== null && boss.visible) {
      const b = boss.userData;
      b.corpo.rotation.y += dt * 0.7;
      b.corpo.rotation.x += dt * 0.25;
      const fracao = b.fracao ?? 0;
      b.frente.scale.x = 2.6 * fracao;
      // A barra encolhe da esquerda para a direita: sem o deslocamento,
      // ela encolheria pelo centro.
      b.frente.position.x = -1.3 * (1 - fracao);
    }
  }

  renderizador.render(cena, camera);
}

redimensionar();
conectar();
animar();
