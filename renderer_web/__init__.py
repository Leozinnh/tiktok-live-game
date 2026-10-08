"""Renderer 3D no navegador.

Segundo renderer do projeto, ao lado do pygame. Prova a promessa da
arquitetura: `game/` nao importa pygame e `GameState.to_dict()` ja existia
para isto, entao trocar de renderer nao muda uma linha da logica do jogo.

Pecas:

- `snapshot`: transforma GameState em JSON. Puro, sem socket.
- `servidor`: sobe o HTTP (arquivos de `web/`) e o WebSocket que publica os
  retratos. Roda em threads proprias e nunca bloqueia o loop do jogo.
"""
