import time

import pygame


class PygameUI:
    def __init__(self, config: dict, game):
        pygame.init()
        pygame.display.set_caption("TikTok LIVE Interactive Game")

        width = config["app"].get("window_width", 1280)
        height = config["app"].get("window_height", 720)
        self.screen = pygame.display.set_mode((width, height))
        self.width = width
        self.height = height

        self.game = game
        self.font = pygame.font.SysFont("Arial", 22)
        self.small = pygame.font.SysFont("Arial", 17)
        self.big = pygame.font.SysFont("Arial", 34, bold=True)

        self.background = (18, 20, 28)
        self.panel = (30, 34, 46)
        self.text = (235, 238, 245)
        self.muted = (160, 165, 178)
        self.green = (65, 210, 120)
        self.red = (230, 75, 80)
        self.blue = (70, 150, 255)
        self.yellow = (245, 200, 65)

    def _text(self, text, x, y, font=None, color=None):
        surface = (font or self.font).render(str(text), True, color or self.text)
        self.screen.blit(surface, (x, y))

    def _bar(self, x, y, w, h, value, maximum, fill):
        pygame.draw.rect(self.screen, (55, 58, 70), (x, y, w, h), border_radius=5)
        ratio = 0 if maximum <= 0 else max(0, min(1, value / maximum))
        pygame.draw.rect(
            self.screen,
            fill,
            (x, y, int(w * ratio), h),
            border_radius=5,
        )

    def draw(self, queue_size: int):
        self.screen.fill(self.background)

        state = self.game.state

        # Título
        self._text("TikTok LIVE — Interactive Game", 35, 25, self.big)
        self._text(
            f"Fila de eventos: {queue_size}",
            1000,
            35,
            self.small,
            self.muted,
        )

        # Arena
        pygame.draw.rect(
            self.screen,
            self.panel,
            (30, 90, 820, 590),
            border_radius=12,
        )

        ground_y = 570
        pygame.draw.line(self.screen, (70, 75, 90), (60, ground_y), (820, ground_y), 3)

        # Personagem
        px = int(self.game.character_x)
        py = int(ground_y - 65 - self.game.character_y)

        body_color = self.yellow
        if time.monotonic() < state.mega_until:
            body_color = (255, 100, 240)
        elif time.monotonic() < state.rage_until:
            body_color = (255, 90, 70)

        pygame.draw.circle(self.screen, body_color, (px, py), 28)
        pygame.draw.rect(self.screen, body_color, (px - 22, py + 20, 44, 45), border_radius=8)

        # Inimigos
        for enemy in state.enemies:
            ex, ey = int(enemy.x), int(enemy.y)
            pygame.draw.rect(self.screen, self.red, (ex, ey, 36, 36), border_radius=6)

        # Painel direito
        pygame.draw.rect(
            self.screen,
            self.panel,
            (875, 90, 375, 590),
            border_radius=12,
        )

        self._text("STATUS", 900, 115, self.big)

        self._text(f"HP: {state.hp}/{state.max_hp}", 900, 165)
        self._bar(900, 195, 310, 18, state.hp, state.max_hp, self.green)

        self._text(f"XP: {state.xp}/{self.game.xp_per_level}", 900, 235)
        self._bar(900, 265, 310, 18, state.xp, self.game.xp_per_level, self.blue)

        self._text(f"Nível: {state.level}", 900, 305)
        self._text(f"Velocidade: {state.speed:.0f}", 900, 340)

        self._text(f"Presentes: {state.total_gifts}", 900, 385)
        self._text(f"Seguidores: {state.total_followers}", 900, 420)
        self._text(f"Compartilhamentos: {state.total_shares}", 900, 455)
        self._text(f"Curtidas: {state.total_likes}", 900, 490)

        self._text("EVENTOS RECENTES", 55, 610, self.font)
        y = 640
        for message in self.game.recent_events[:2]:
            self._text(message[:85], 55, y, self.small, self.muted)
            y += 20

        # Mais eventos na arena inferior/esquerda
        y = 115
        for message in self.game.recent_events[2:10]:
            self._text(message[:55], 55, y, self.small, self.muted)
            y += 22

        pygame.display.flip()

    def close(self):
        pygame.quit()
