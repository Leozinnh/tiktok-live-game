/*
  Geometria da cena: unidades do jogo, limites da arena e enquadramento
  da camera.

  Este arquivo existe separado de `jogo.js` por um motivo pratico: e a
  unica parte do renderer que da para conferir sem navegador. Nao toca no
  DOM e nao cria WebGL, entao roda no Node — e o enquadramento, que e o
  erro mais provavel de passar despercebido (personagem cortado na borda),
  vira uma verificacao de verdade em vez de um palpite.

  Ver: `.superpowers/sdd/<plano>/verifica_camera.mjs`
*/

import * as THREE from './vendor/three.module.min.js';

// ---------------------------------------------------------------- unidades

/*
  A arena do jogo tem 1080x1920 unidades logicas, com Y crescendo para
  BAIXO (convencao de tela). O mundo do Three.js tem Y para CIMA e o chao
  no plano XZ. A conversao:
      mundo.x = (jogo.x - 540) / 100
      mundo.z = (jogo.y - 960) / 100
  O divisor 100 so escolhe uma escala confortavel para camera e luz.
*/
export const ESCALA = 100;
export const MEIA_LARGURA = 540;
export const MEIO_COMPRIMENTO = 960;

export const jx = (x) => (x - MEIA_LARGURA) / ESCALA;
export const jz = (y) => (y - MEIO_COMPRIMENTO) / ESCALA;

// Faixa da arena que fica realmente visivel: entre o HUD (320) e o feed
// (1490), igual ao layout do pygame. O resto existe no jogo mas fica
// escondido atras dos paineis.
export const TOPO_JOGO = 320;
export const BASE_JOGO = 1490;

export const ARENA = {
  largura: 1080 / ESCALA,
  topo: jz(TOPO_JOGO),
  base: jz(BASE_JOGO),
};
ARENA.profundidade = ARENA.base - ARENA.topo;
ARENA.centroZ = (ARENA.topo + ARENA.base) / 2;

/*
  Angulo da camera, em graus, medido do chao. 90 seria vista de cima; 0
  seria na altura dos olhos.

  O 45 nao e chute: e o unico meio-termo entre duas exigencias que brigam.
  Quanto mais deitada a camera, mais o chao encolhe na vertical (por
  sin(angulo)) e mais sobra de quadro em cima e embaixo — mas tambem mais
  alto o personagem aparece. Quanto mais em pe, mais o quadro enche e mais
  o personagem some. Medido, no palco 9:16:

      angulo   quadro ocupado   altura do personagem
        35         49%                12,1%
        45         62%                10,2%
        55         73%                 7,8%
        70         79%                 0,8%   <- personagem ilegivel

  Aos 45 o personagem sai do mesmo tamanho que saia no renderer pygame
  (cerca de 10% do painel) e quase dois tercos do quadro ficam ocupados.
*/
export const INCLINACAO = 45;

// Altura do alvo: um pouco acima do chao, para o corpo do personagem
// ficar no meio do quadro em vez de colado na base.
export const ALTURA_ALVO = 0.4;

/*
  Sobra de chao em volta da arena. Nao e enfeite: a nevoa precisa de mundo
  para se dissolver. Se o chao terminasse na borda da arena, apareceria uma
  aresta dura no horizonte, e a aresta anda junto com a camera.
*/
export const SOBRA_CHAO = 26;

export const CHAO = {
  largura: ARENA.largura + SOBRA_CHAO * 2,
  z0: ARENA.topo - SOBRA_CHAO,
  z1: ARENA.base + SOBRA_CHAO,
};
CHAO.centroZ = (CHAO.z0 + CHAO.z1) / 2;
CHAO.profundidade = CHAO.z1 - CHAO.z0;

// ---------------------------------------------------------------- camera

export function direcaoDaCamera(inclinacao = INCLINACAO) {
  return new THREE.Vector3(
    0,
    Math.sin(THREE.MathUtils.degToRad(inclinacao)),
    Math.cos(THREE.MathUtils.degToRad(inclinacao)),
  ).normalize();
}

export function alvoDaCamera() {
  return new THREE.Vector3(0, ALTURA_ALVO, ARENA.centroZ);
}

/** Os quatro cantos do chao visivel. E o que a camera precisa enquadrar. */
export function cantosDaArena() {
  return [
    new THREE.Vector3(-ARENA.largura / 2, 0, ARENA.topo),
    new THREE.Vector3(ARENA.largura / 2, 0, ARENA.topo),
    new THREE.Vector3(-ARENA.largura / 2, 0, ARENA.base),
    new THREE.Vector3(ARENA.largura / 2, 0, ARENA.base),
  ];
}

/**
 * Afasta a camera ate os quatro cantos caberem, e devolve a distancia.
 *
 * A formula fecharia a conta para o plano do alvo, mas com a camera
 * inclinada a borda perto fica mais estreita que a de tras — e o
 * personagem, que anda encostado nessa borda, sairia cortado nas laterais.
 * Aqui a gente projeta os cantos de verdade e afasta ate caberem.
 *
 * O passo de 2% importa: o laco para na PRIMEIRA distancia que serve, e
 * um passo grosso erra para mais — sobra quadro que nao precisava sobrar.
 * Com 5% a camera ficava longe demais e o personagem encolhia junto. Custa
 * uma centena de iteracoes, uma vez por redimensionamento.
 *
 * @param limite  fracao do quadro que os cantos podem ocupar. 0.96 deixa
 *                4% de folga em cada borda.
 */
export function enquadrar(
  camera,
  { alvo = alvoDaCamera(), direcao = direcaoDaCamera(), cantos = cantosDaArena(), limite = 0.96 } = {},
) {
  let distancia = 8;

  for (let passo = 0; passo < 120; passo++) {
    camera.position.copy(alvo).addScaledVector(direcao, distancia);
    camera.lookAt(alvo);
    camera.updateMatrixWorld(true);

    const cortado = cantos.some((canto) => {
      const p = canto.clone().project(camera);
      return Math.abs(p.x) > limite || Math.abs(p.y) > limite;
    });
    if (!cortado) break;
    distancia *= 1.02;
  }

  return distancia;
}

/** Camera nova, ja enquadrada, para a proporcao informada. */
export function criarCamera(largura, altura, fov = 45) {
  const camera = new THREE.PerspectiveCamera(fov, largura / Math.max(1, altura), 0.1, 200);
  camera.updateProjectionMatrix();
  enquadrar(camera);
  return camera;
}

// ------------------------------------------------------------------ nevoa

const AMOSTRAS = 9;

/*
  Amostra um retangulo do chao numa grade. Os quatro cantos sozinhos
  enganam: o ponto mais proximo de um retangulo visto de cima costuma cair
  no meio de uma aresta, nao num canto. Uma grade de 9x9 erra pouco e nao
  custa nada — roda uma vez por redimensionamento.

  Com z0 === z1 a grade degenera numa linha: e assim que se amostra a
  borda de tras do chao.
*/
function grade(largura, z0, z1, passos = AMOSTRAS) {
  const pontos = [];
  for (let i = 0; i < passos; i++) {
    for (let j = 0; j < passos; j++) {
      pontos.push(new THREE.Vector3(
        -largura / 2 + (largura * i) / (passos - 1),
        0,
        z0 + ((z1 - z0) * j) / (passos - 1),
      ));
    }
  }
  return pontos;
}

function extremos(camera, pontos) {
  let perto = Infinity;
  let longe = -Infinity;
  for (const ponto of pontos) {
    const d = camera.position.distanceTo(ponto);
    if (d < perto) perto = d;
    if (d > longe) longe = d;
  }
  return { perto, longe };
}

/**
 * O alcance da nevoa, medido a partir da camera enquadrada.
 *
 * A nevoa tem duas exigencias e as duas sao faceis de errar:
 *
 * - ela NAO pode comecar sobre a arena. O inimigo nasce no fundo da tela e
 *   o chefe fica la; se a nevoa pegar neles, o jogo some justamente onde a
 *   acao comeca. Entao `near` fica depois do ponto mais distante da arena.
 *
 * - ela PRECISA terminar antes da borda do chao. Senao aparece a aresta do
 *   plano no horizonte. A borda que aparece e a de tras, e o ponto mais
 *   proximo dessa borda e o do meio — entao e ele que manda em `far`.
 *
 * Como as duas medidas saem da posicao da camera, elas andam junto quando
 * a camera se afasta. Um `Fog(16, 30)` fixo nao acompanha: com a camera a
 * 19 unidades a nevoa comecava a 16 e o fundo da arena ja aparecia lavado.
 */
export function nevoaDaCamera(camera, { folga = 1.08 } = {}) {
  const arena = extremos(camera, grade(ARENA.largura, ARENA.topo, ARENA.base));
  const bordaDeTras = extremos(camera, grade(CHAO.largura, CHAO.z0, CHAO.z0));

  const near = arena.longe * folga;
  return { near, far: Math.max(bordaDeTras.perto, near * 1.15) };
}
