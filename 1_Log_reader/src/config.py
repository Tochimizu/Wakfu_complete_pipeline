
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


#datapath_1 = f"C:\Users\MediaMonster\AppData\Roaming\zaap\gamesLogs\wakfu\logs\wakfu.log"
datapath_2 = f"C:/Users/MediaMonster/AppData/Roaming/zaap/gamesLogs/wakfu/logs/wakfu.log"
