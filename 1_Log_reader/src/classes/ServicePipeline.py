from src.config import *
from pathlib import Path
# -----------------------------
# SERVICE PIPELINE
# -----------------------------
from src.classes.GameState import GameState
from src.classes.LogParser import FightLogParser
from src.classes.Bot import PvEEngine
from src.classes.FileReader import FileTailer


class FightLogService:
    def __init__(self, file_path: Path):
        self.state = GameState()
        self.queue = asyncio.Queue(maxsize=1000)
        self.tailer = FileTailer(file_path, self.queue)
        self.worker_task: Optional[asyncio.Task] = None
        self.ai = PvEEngine()

    async def start(self):
        print("Listening for fight logs...")
        self.worker_task = asyncio.create_task(self.worker())
        asyncio.create_task(self.debug_loop()) # optional debug console print loop
        await self.tailer.start()

    async def stop(self):
        self.tailer.stop()
        if self.worker_task:
            self.worker_task.cancel()

    async def worker(self):
        while True:
            line = await self.queue.get()

            event = FightLogParser.parse(line)
            if not event:
                continue

            await self.state.apply(event)

            # PvE hook (future intelligence layer)
            state = await self.state.get_fight(event.fight_id)
            self.ai.on_state_update(event.fight_id, state)
    async def debug_loop(self):
        while True:
            await self.state.display()
            await asyncio.sleep(5)
