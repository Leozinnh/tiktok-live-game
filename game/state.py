from dataclasses import dataclass, field

from game.entities import Boss, Character, Enemy


@dataclass
class GameState:
    """Estado do jogo. Dados puros: nenhum import de pygame.

    `to_dict()` existe para que um renderer futuro (navegador, Unity) possa
    consumir o mesmo estado sem que a logica do jogo mude.
    """

    hp: int = 100
    max_hp: int = 100
    xp: int = 0
    level: int = 1
    speed: float = 220.0
    base_speed: float = 220.0

    character: Character = field(default_factory=Character)
    enemies: list[Enemy] = field(default_factory=list)
    boss: Boss | None = None

    # Preenchidos pela Task 7.
    effects: object | None = None
    announcements: object | None = None

    # Copia do vetor de intencao, so para o renderer desenhar a faixa de
    # direcao. O motor e a fonte da verdade; este campo e somente leitura.
    intent_display: float = 0.0

    total_gifts: int = 0
    total_likes: int = 0
    total_followers: int = 0
    total_shares: int = 0

    def to_dict(self) -> dict:
        return {
            "hp": self.hp,
            "max_hp": self.max_hp,
            "xp": self.xp,
            "level": self.level,
            "speed": self.speed,
            "character": {
                "x": self.character.x,
                "y": self.character.y,
                "y_offset": self.character.y_offset,
                "facing": self.character.facing,
            },
            "enemies": [
                {"x": e.x, "y": e.y, "hp": e.hp, "radius": e.radius}
                for e in self.enemies
            ],
            "boss": (
                None
                if self.boss is None
                else {
                    "x": self.boss.x,
                    "y": self.boss.y,
                    "hp": self.boss.hp,
                    "max_hp": self.boss.max_hp,
                    "radius": self.boss.radius,
                }
            ),
            "total_gifts": self.total_gifts,
            "total_likes": self.total_likes,
            "total_followers": self.total_followers,
            "total_shares": self.total_shares,
        }
