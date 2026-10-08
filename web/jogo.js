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
import { ARENA, CHAO, ESCALA, criarCamera, enquadrar, jx, jz, nevoaDaCamera } from './camera.js';

// ------------------------------------------------------------------ cores

const COR = {
  fundo: 0x0e1018,
  chao: 0x3a4052,
  grade: 0x262c3c,
  personagem: 0xfad658,
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

// O chao e a mesma constante que a nevoa usa para saber onde terminar. Se
// os dois saissem de contas diferentes, a aresta do plano apareceria.
const chao = new THREE.Mesh(
  new THREE.PlaneGeometry(CHAO.largura, CHAO.profundidade),
  new THREE.MeshStandardMaterial({ color: COR.chao, roughness: 0.95, metalness: 0 }),
);
chao.rotation.x = -Math.PI / 2;
chao.position.z = CHAO.centroZ;
chao.receiveShadow = true;
cena.add(chao);

// Grade por cima do chao. E o que da a referencia de movimento quando o
// personagem anda: sem ela, um fundo liso nao mostra velocidade nenhuma.
const grade = new THREE.GridHelper(
  CHAO.profundidade,
  Math.round(CHAO.profundidade),
  COR.grade,
  COR.grade,
);
grade.position.set(0, 0.01, CHAO.centroZ);
grade.material.transparent = true;
grade.material.opacity = 0.55;
cena.add(grade);

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
  const material = new THREE.MeshStandardMaterial({
    color: COR.personagem, roughness: 0.45, metalness: 0.1,
  });

  const peca = (w, h, d, x, y, z) => {
    const malha = new THREE.Mesh(new THREE.BoxGeometry(w, h, d), material);
    malha.position.set(x, y, z);
    malha.castShadow = true;
    grupo.add(malha);
    return malha;
  };

  const corpo = peca(0.78, 0.92, 0.52, 0, 0.92, 0);
  const cabeca = peca(0.54, 0.52, 0.52, 0, 1.66, 0);
  const bracoE = peca(0.2, 0.62, 0.2, -0.49, 0.86, 0);
  const bracoD = peca(0.2, 0.62, 0.2, 0.49, 0.86, 0);
  const pernaE = peca(0.24, 0.52, 0.24, -0.19, 0.20, 0);
  const pernaD = peca(0.24, 0.52, 0.24, 0.19, 0.20, 0);

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

  grupo.userData = { corpo, cabeca, bracoE, bracoD, pernaE, pernaD, escudo, material };
  return grupo;
}

function criarInimigo() {
  const malha = new THREE.Mesh(
    new THREE.OctahedronGeometry(0.42, 0),
    new THREE.MeshStandardMaterial({
      color: COR.inimigo, roughness: 0.4, metalness: 0.2,
      emissive: COR.inimigo, emissiveIntensity: 0.25,
    }),
  );
  malha.castShadow = true;
  return malha;
}

function criarBoss() {
  const grupo = new THREE.Group();
  const corpo = new THREE.Mesh(
    new THREE.DodecahedronGeometry(1.25, 0),
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
    if (melhor === null) {
      malha.position.set(desejado.x, 0.55, desejado.z);
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
    const andando = Math.abs(d.character.x - personagem.position.x) > 0.005;
    const passo = Math.sin(tempo * 11) * (andando ? 0.24 : 0.05);
    c.pernaE.rotation.x = passo;
    c.pernaD.rotation.x = -passo;
    c.bracoE.rotation.x = -passo * 0.7;
    c.bracoD.rotation.x = passo * 0.7;
    c.corpo.position.y = 0.92 + Math.abs(Math.sin(tempo * 5.5)) * 0.035;

    // y_offset e o pulo, em unidades do jogo.
    personagem.position.y = (d.character.y_offset ?? 0) / ESCALA;

    // facing: -1 encara a esquerda. Vira o grupo inteiro.
    personagem.rotation.y = d.character.facing >= 0 ? 0 : Math.PI;

    c.escudo.visible = 'shield' in viva;
    if (c.escudo.visible) {
      const pulso = 1 + Math.sin(tempo * 6) * 0.04;
      c.escudo.scale.setScalar(pulso);
    }

    // mega: o personagem cresce e passa a brilhar.
    const mega = 'mega' in viva;
    c.material.emissive.setHex(mega ? COR.mega : 0x000000);
    c.material.emissiveIntensity = mega ? 0.6 : 0;
    personagem.scale.setScalar(mega ? 1.35 : 1);

    // --- inimigos
    for (const malha of poolInimigos) {
      if (!malha.visible) continue;
      malha.rotation.y += dt * 2.4;
      malha.position.y = 0.55 + Math.sin(tempo * 3 + malha.position.x) * 0.09;
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
