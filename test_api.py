

import asyncpg
import json
import asyncio
import logging
from FarmClass import FarmPLC,FarmList,PointTag
import uvicorn
from fastapi import FastAPI,Request,HTTPException,Header
from uvicorn.main import Server
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi.responses import HTMLResponse
from logging.handlers import RotatingFileHandler
from typing import Optional,Union

from fastapi import FastAPI, Header

app = FastAPI()


@app.post("/items/")
async def read_items(*, user_agent: str = Header(None)):
    return {"User-Agent": user_agent}


config = uvicorn.Config(app, host='0.0.0.0', port=8000, log_level="info")
server = uvicorn.Server(config) 

async def main():
    try:
        await server.serve()
    except asyncio.exceptions.CancelledError:
         return 0  
if __name__ == "__main__":           
  asyncio.run(main())