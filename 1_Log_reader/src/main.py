from src.classes.ServicePipeline import *
from src.classes.GameState import IsoCoordinateMapper, IsoConfig

from src.config import *
from pathlib import Path

LOG_FILE = Path("data_test/test_logs.txt")
# -----------------------------
# FASTAPI APP
# -----------------------------
service = FightLogService(LOG_FILE)

@asynccontextmanager
async def lifespan(app: FastAPI):
    mapper = IsoCoordinateMapper(
        IsoConfig(
            tile_width=64,
            tile_height=32,
            offset_x=0,   # later loaded from calibration
            offset_y=0,
            anchor_x=0,
            anchor_y=0,
        )
    )

    service.state.attach_mapper(mapper)

    task = asyncio.create_task(service.start())
    yield
    await service.stop()
    task.cancel()

app = FastAPI(lifespan=lifespan)


@app.get("/")
async def root():
    return {"status": "ok"}


@app.get("/state")
async def get_all_state():
    return await service.state.get_all()


@app.get("/state/{fight_id}")
async def get_fight_state(fight_id: str):
    return await service.state.get_fight(fight_id)

@app.get("/debug/state")
async def debug_state():
    await service.state.display()
    return {"status": "printed"}

@app.get("/dashboard", response_class=HTMLResponse)
async def dashboard():
    html = """<!DOCTYPE html>
<html>
    <head>
        <title>PvE Debug Dashboard</title>
        <style>
            body {
                font-family: Arial;
                background: #0f1117;
                color: #e6e6e6;
                margin: 0;
                padding: 20px;
            }

            h1 {
                color: #7dd3fc;
            }

            .fight {
                background: #1a1d25;
                padding: 15px;
                margin-bottom: 15px;
                border-radius: 10px;
            }

            .entity {
                padding: 5px 0;
                border-bottom: 1px solid #2a2f3a;
            }

            .ai {
                color: #fca5a5;
            }

            .player {
                color: #86efac;
            }

            .meta {
                font-size: 12px;
                opacity: 0.7;
            }
        </style>
    </head>
    <body>

    <h1>🧭 PvE Game State Dashboard</h1>
    <div id="root">Loading...</div>

    <script>
    async function fetchState() {
        const res = await fetch('/state');
        const data = await res.json();

        const root = document.getElementById('root');
        root.innerHTML = '';

        for (const [fightId, fight] of Object.entries(data)) {
            const div = document.createElement('div');
            div.className = 'fight';

            let html = `<h2>⚔️ Fight ${fightId}</h2>`;
            html += `<div class="meta">Entities: ${Object.keys(fight.entities).length}</div>`;

            for (const [id, e] of Object.entries(fight.entities)) {
                const cls = e.isAI ? 'entity ai' : 'entity player';
                const pos = e.position;

                html += `
                    <div class="${cls}">
                        <b>${e.name}</b> (breed ${e.breed})<br/>
                        <span class="meta">
                            id=${id} | pos=(${pos.x},${pos.y},${pos.z}) | ${e.isAI ? 'AI' : 'PLAYER'}
                        </span>
                    </div>
                `;
            }

            div.innerHTML = html;
            root.appendChild(div);
        }
    }

    setInterval(fetchState, 1000);
    fetchState();
    </script>

    </body>
</html>"""
    return html