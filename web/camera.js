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

  Aqui so ha uma troca, e ela e direta: quanto mais deitada a camera, mais
  o chao encolhe na vertical (por sin(angulo)) e mais o quadro enche — mas
  menor o personagem fica. Medido com a camera enquadrada, no palco 9:16,
  com o personagem inteiro dentro do quadro:

      angulo   distancia   quadro ocupado   altura do personagem
        35        32,4          46%                11,6%
        40        32,5          51%                10,5%
        45        32,5          56%                 9,3%
        50        32,0          61%                 8,2%
        55        32,0          65%                 6,9%
        60        32,1          69%                 5,6%

  A distancia quase nao muda (32 +- 0,5): quem manda nela e o personagem
  encostado na parede, que e a exigencia mais larga. O angulo so decide
  como o quadro se reparte entre chao e personagem.

  O 45 e onde o personagem sai do mesmo tamanho que saia no renderer pygame
  (cerca de 10% do painel) — as duas versoes do jogo ficam parecidas de
  longe, que e o que o publico ve no celular.
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

/** Os quatro cantos do chao visivel. */
export function cantosDaArena() {
  return [
    new THREE.Vector3(-ARENA.largura / 2, 0, ARENA.topo),
    new THREE.Vector3(ARENA.largura / 2, 0, ARENA.topo),
    new THREE.Vector3(-ARENA.largura / 2, 0, ARENA.base),
    new THREE.Vector3(ARENA.largura / 2, 0, ARENA.base),
  ];
}

/*
  Ate onde o personagem vai, ja contando o corpo dele.

  `_mover_personagem` prende o CENTRO entre 34 e 1046 (`Character.radius`)
  e `Character.y` e 1400 fixo — ele so anda para os lados. O corpo passa 59
  unidades disso para cada lado (os bracos ficam em +-0,49 e ainda tem
  espessura) e o topo da cabeca fica em 1,96.

  Ficam de fora, de proposito, o escudo (esfera de raio 1,15) e o efeito
  mega, que cresce 35%. Os dois sao passageiros: enquadrar por eles
  encolheria o personagem para sempre por causa de um efeito de dez
  segundos. No mega encostado na parede a cabeca sai alguns pixels do
  quadro — e o preco de nao pagar esse preco o resto do tempo.
*/
export const PASSEIO = {
  esquerda: 34,
  direita: 1046,
  corpo: 59,
  y: 1400,
  altura: 1.96,
};

/*
  O piso VISIVEL: a arena mais a largura do corpo do personagem.

  Nao e a arena do jogo (0..1080) — e onde o personagem consegue PISAR. O
  motor prende o centro dele entre 34 e 1046, mas o corpo passa 59 unidades
  disso para cada lado. Com o piso terminando em 1080, ele encostava na
  parede e metade do corpo ficava pendurada fora do piso, sobre o terreno
  escuro, como se fosse cair da plataforma.

  Quem desenha a borda e a grade usa este retangulo, e nao `ARENA`: a
  fronteira que o publico ve tem que ser a que ele consegue alcancar.
*/
export const PISO = {
  largura: ARENA.largura + (PASSEIO.corpo / ESCALA) * 2,
  topo: ARENA.topo,
  base: ARENA.base,
};
PISO.profundidade = PISO.base - PISO.topo;
PISO.centroZ = (PISO.topo + PISO.base) / 2;

/**
 * Tudo o que a camera PRECISA enquadrar.
 *
 * Nao basta enquadrar a arena. O personagem anda encostado nas paredes, e
 * no extremo ele passa da borda — enquadrar so os cantos deixava a cabeca
 * dele sair da tela na parede direita (ndc.x = 1,006). O defeito so
 * aparecia depois que alguem mandava o boneco para la, ao vivo.
 */
export function pontosObrigatorios() {
  const pontos = cantosDaArena();
  for (const x of [PASSEIO.esquerda - PASSEIO.corpo, PASSEIO.direita + PASSEIO.corpo]) {
    for (const altura of [0, PASSEIO.altura]) {
      pontos.push(new THREE.Vector3(jx(x), altura, jz(PASSEIO.y)));
    }
  }
  return pontos;
}

/**
 * Afasta a camera ate tudo o que importa caber, e devolve a distancia.
 *
 * A formula fecharia a conta para o plano do alvo, mas com a camera
 * inclinada a borda perto fica mais estreita que a de tras — e o
 * personagem, que anda encostado nessa borda, sairia cortado nas laterais.
 * Aqui a gente projeta os pontos de verdade e afasta ate caberem.
 *
 * Os pontos sao `pontosObrigatorios()`, nao so os cantos da arena: o
 * personagem anda pelas paredes e a cabeca dele passa da borda.
 *
 * O passo de 2% importa: o laco para na PRIMEIRA distancia que serve, e
 * um passo grosso erra para mais — sobra quadro que nao precisava sobrar.
 * Com 5% a camera ficava longe demais e o personagem encolhia junto. Custa
 * uma centena de iteracoes, uma vez por redimensionamento.
 *
 * @param limite  fracao do quadro que os pontos podem ocupar. 0.96 deixa
 *                4% de folga em cada borda.
 */
export function enquadrar(
  camera,
  { alvo = alvoDaCamera(), direcao = direcaoDaCamera(), pontos = pontosObrigatorios(), limite = 0.96 } = {},
) {
  let distancia = 8;

  for (let passo = 0; passo < 120; passo++) {
    camera.position.copy(alvo).addScaledVector(direcao, distancia);
    camera.lookAt(alvo);
    camera.updateMatrixWorld(true);

    const cortado = pontos.some((ponto) => {
      const p = ponto.clone().project(camera);
      return Math.abs(p.x) > limite || Math.abs(p.y) > limite;
    });
    if (!cortado) break;
    distancia *= 1.02;
  }

  return distancia;
}

/*
  Campo de visao. Estreito de proposito — e o segundo ajuste que faz o
  personagem caber GRANDE.

  Com a camera inclinada, quem manda no enquadramento e o canto perto: ele
  esta mais perto da lente que o fundo, entao aparece maior e e ele que
  toca a borda primeiro. Uma lente aberta acentua essa diferenca e obriga a
  camera a recuar — ou seja, o personagem encolhe por causa de um canto que
  ninguem esta olhando. Fechando a lente, as distancias relativas se
  comprimem, o canto perto para de mandar e a camera pode chegar perto.

  Medido, aos 45 graus, com o personagem inteiro dentro do quadro:

      fov   distancia   quadro ocupado   altura do personagem
       45      20,3          51%                8,1%
       32      27,3          54%                8,8%
       26      32,6          56%                9,1%
       20      41,4          57%                9,4%

  O 26 e onde a curva dobra: de 20 para 26 ganha-se o mesmo que de 45 para
  26 em tamanho, e a partir dali so se paga distancia. Continua sendo
  perspectiva de verdade — o inimigo do fundo ainda aparece menor que o da
  frente —, so nao e mais grande-angular.
*/
export const CAMPO_DE_VISAO = 26;

/** Camera nova, ja enquadrada, para a proporcao informada. */
export function criarCamera(largura, altura, fov = CAMPO_DE_VISAO) {
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
  // PISO, nao ARENA: o piso e maior e e ele que aparece. Amostrar a arena
  // deixaria os cantos do piso de fora da conta — justamente os pontos mais
  // distantes, que sao os que decidem onde a nevoa pode comecar.
  const piso = extremos(camera, grade(PISO.largura, PISO.topo, PISO.base));
  const bordaDeTras = extremos(camera, grade(CHAO.largura, CHAO.z0, CHAO.z0));

  const near = piso.longe * folga;
  return { near, far: Math.max(bordaDeTras.perto, near * 1.15) };
}
