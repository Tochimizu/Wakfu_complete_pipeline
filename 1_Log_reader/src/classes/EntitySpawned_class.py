from src.config import *

# -----------------------------
# EVENTS (PvE foundation)
# -----------------------------
@dataclass
class EntitySpawned:
    fight_id: str
    entity_id: str
    name: str
    breed: int
    is_ai: bool
    obstacle_id: int
    position: dict
