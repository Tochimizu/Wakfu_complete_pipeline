import re
from dataclasses import dataclass
from typing import Dict, Optional, Any

from fastapi import FastAPI
from pathlib import Path
import asyncio
from fastapi.responses import HTMLResponse
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.templating import Jinja2Templates
from src.classes.EntitySpawned_class import EntitySpawned

# -----------------------------
# PARSER → EVENT MAPPER
# -----------------------------
class FightLogParser:
    FL_REGEX = re.compile(
        r"\[_FL_\]\s+fightId=(\d+)\s+"
        r"(.*?)\s+breed\s+:\s+(\d+)\s+\[([-\d]+)\]\s+"
        r"isControlledByAI=(true|false)\s+obstacleId\s+:\s+([-\d]+)\s+"
        r"join the fight at\s+\{Point3\s+:\s+\(([-\d]+),\s+([-\d]+),\s+([-\d]+)\)\}"
    )

    @staticmethod
    def parse(line: str) -> Optional[EntitySpawned]:
        if "[_FL_]" not in line:
            return None

        m = FightLogParser.FL_REGEX.search(line)
        if not m:
            return None

        fight_id, name, breed, entity_id, is_ai, obstacle_id, x, y, z = m.groups()

        return EntitySpawned(
            fight_id=fight_id,
            entity_id=entity_id,
            name=name.strip(),
            breed=int(breed),
            is_ai=(is_ai == "true"),
            obstacle_id=int(obstacle_id),
            position={"x": int(x), "y": int(y), "z": int(z)},
        )

