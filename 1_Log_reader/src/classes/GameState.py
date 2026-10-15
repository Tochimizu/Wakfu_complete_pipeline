# -----------------------------
# GAME STATE (PvE truth model)
# -----------------------------
from src.classes.EntitySpawned_class import EntitySpawned
from src.config import *

from dataclasses import dataclass   
from typing import Tuple

@dataclass
class IsoConfig:
    tile_width: int = 64   # pixel width of tile
    tile_height: int = 32  # pixel height of tile

    # calibration offsets (learned from your click data)
    offset_x: int = 0
    offset_y: int = 0

    # camera anchor shift (player-centered correction)
    anchor_x: int = 0
    anchor_y: int = 0

class IsoGrid:
    def __init__(self, origin_x, origin_y, tile_w=45, tile_h=80):
        self.ox = origin_x
        self.oy = origin_y
        self.tw = tile_w
        self.th = tile_h

    def tile_to_screen(self, x, y):
        sx = self.ox + (x - y) * (self.tw / 2)
        sy = self.oy + (x + y) * (self.th / 2)
        return int(sx), int(sy)

    def screen_to_tile(self, sx, sy):
        x = ((sy / (self.th/2)) + (sx / (self.tw/2))) / 2
        y = ((sy / (self.th/2)) - (sx / (self.tw/2))) / 2
        return round(x), round(y)
    

class IsoCoordinateMapper:
    def __init__(self, config: IsoConfig):
        self.cfg = config

    def world_to_screen(self, x: int, y: int) -> Tuple[int, int]:
        """
        Standard isometric projection + calibration offsets
        """

        # isometric projection
        screen_x = (x - y) * (self.cfg.tile_width // 2)
        screen_y = (x + y) * (self.cfg.tile_height // 2)

        # apply calibration offsets + camera anchor correction
        screen_x += self.cfg.offset_x + self.cfg.anchor_x
        screen_y += self.cfg.offset_y + self.cfg.anchor_y

        return screen_x, screen_y


class GameState:
    def __init__(self):
        self.fights: Dict[str, Dict[str, Any]] = {}
        self.lock = asyncio.Lock()
        self.mapper: Optional[IsoCoordinateMapper] = None

    def attach_mapper(self, mapper: IsoCoordinateMapper):
        self.mapper = mapper

    def world_to_cursor(self, pos: dict):
        if not self.mapper:
            return None
        return self.mapper.world_to_screen(pos["x"], pos["y"])

    async def apply(self, event: EntitySpawned):
        async with self.lock:
            fight = self.fights.setdefault(event.fight_id, {"entities": {}})

            fight["entities"][event.entity_id] = {
                "name": event.name,
                "breed": event.breed,
                "isAI": event.is_ai,
                "obstacleId": event.obstacle_id,
                "position": event.position,
            }

    async def get_all(self):
        async with self.lock:
            return self.fights

    async def get_fight(self, fight_id: str):
        async with self.lock:
            return self.fights.get(fight_id)

    async def display(self):
        async with self.lock:
            if not self.fights:
                print("GameState: no active fights")
                return

            print("\n" + "=" * 60)
            print("GAME STATE SNAPSHOT")
            print("=" * 60)

            for fight_id, fight in self.fights.items():
                entities = fight.get("entities", {})

                print(f"\n Fight {fight_id}")
                print(f"   Entities: {len(entities)}")

                for entity_id, e in entities.items():
                    pos = e["position"]
                    cursor = self.world_to_cursor(e["position"])


                    tag = "AI" if e["isAI"] else "PLAYER"
                    print(
                        f"   ├─ ID : {entity_id} [{tag}] "
                        f"\n\t{e['name']} (breed={e['breed']}) "
                        f"\n\tpos=({pos['x']},{pos['y']},{pos['z']})"
                        f"\n\tcursor={cursor}"
                        

                    )

            print("=" * 60 + "\n")
