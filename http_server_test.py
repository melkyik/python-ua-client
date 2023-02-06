import uvicorn

from uvicorn.main import Server
from fastapi import FastAPI,Request
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi.responses import HTMLResponse
import asyncio

app=FastAPI()
templates=Jinja2Templates(directory="static")
app.mount("/static", StaticFiles(directory="static"), name="static")

@app.get("/",response_class=HTMLResponse )
async def index(request:Request):
    context = {'request':request}
    return templates.TemplateResponse("farminfo.html",context) 



async def main():
    config = uvicorn.Config(app, port=8000, log_level="info")
    server = uvicorn.Server(config) 
    await server.serve()

if __name__ == "__main__":           
    asyncio.run(main()) 