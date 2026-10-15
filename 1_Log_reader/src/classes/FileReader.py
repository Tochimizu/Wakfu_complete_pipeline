from src.config import *
# -----------------------------
# FILE TAILER (async-safe I/O)
# -----------------------------
class FileTailer:
    def __init__(self, file_path: Path, queue: asyncio.Queue):
        self.file_path = file_path
        self.queue = queue
        self.position = 0
        self.running = True

    async def init(self):
        self.file_path.parent.mkdir(parents=True, exist_ok=True)

    async def read_new(self):
        if not self.file_path.exists():
            return

        def _read():
            with self.file_path.open("r", encoding="utf-8") as f:
                f.seek(self.position)
                lines = f.readlines()
                pos = f.tell()
            return lines, pos

        lines, pos = await asyncio.to_thread(_read)

        for line in lines:
            await self.queue.put(line.rstrip("\n"))

        self.position = pos

    async def start(self):
        await self.init()
        while self.running:
            await self.read_new()
            await asyncio.sleep(0.5)

    def stop(self):
        self.running = False
