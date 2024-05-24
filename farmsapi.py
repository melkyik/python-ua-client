import asyncpg
import json
import asyncio
import logging
from FarmClass import FarmPLC,FarmList,PointTag,extract_point_name
import uvicorn
from fastapi import FastAPI,Request,HTTPException,Header,Depends
from uvicorn.main import Server
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi.responses import HTMLResponse
from logging.handlers import RotatingFileHandler
from typing import Optional,Union,List
import farms_logger

mylogger = logging.getLogger(__name__)
mylogger.handlers.clear()

mylogger.addHandler(farms_logger.file_handler)
mylogger.addHandler(farms_logger.console_handler)

# Disable propagation to prevent log records from being passed up to the root logger
mylogger.propagate = False


original_handler = Server.handle_exit

class AppStatus:
    should_exit = False

    @staticmethod
    def handle_exit(*args, **kwargs):
        AppStatus.should_exit = True
        original_handler(*args, **kwargs)
    @staticmethod
    async def terminate(): #для остановки всех процессов ASYNC после выключения веб сервера сам он почемуто не останавливается

          while True:
            if AppStatus.should_exit:
                for task in asyncio.all_tasks():
                    task.cancel()
                try:
                    await task
                except asyncio.CancelledError:
                     mylogger.info("Task cancelled")
            await asyncio.sleep(0.1)
Server.handle_exit = AppStatus.handle_exit

#https://coderoad.ru/58133694/%D0%93%D1%80%D0%B0%D0%BC%D0%BE%D1%82%D0%BD%D0%BE%D0%B5-%D0%BE%D1%82%D0%BA%D0%BB%D1%8E%D1%87%D0%B5%D0%BD%D0%B8%D0%B5-uvicorn-starlette-app-%D1%81-websockets
#https://stackoverflow.com/questions/56052748/python-asyncio-task-cancellation
def smart_round(text, ndigits: int = 2) -> str:
      
        try:
            if text in (True,False):
                return str(text)
            s=float(round(float(text), ndigits))
            return s
        except :
            return str(text)


####=================================================
#веб сервак
#====================================================
app=FastAPI()
async def get_farm_list():
    # Получение экземпляра FarmList из зависимостей FastAPI
    return app.state.farms

templates=Jinja2Templates(directory="static")
app.mount("/static", StaticFiles(directory="static"), name="static")

@app.get("/",response_class=HTMLResponse)
async def index(request:Request, farms: FarmList = Depends(get_farm_list)):
    context = {'request':request, "farms":[]}
    for k in farms:
            fr={}
            fr["id"]=k
            fr["name"]=farms.get(k).name
            fr["connection"]=farms.get(k).connectionstatus
            fr["URL"]=farms.get(k).URL
            fr["values"]=[]
            for v in farms.get(k).Value:
                                    vl={}
                                    tag=farms.get(k).getTagByShort(v)
                                    vl["name"]=tag.name
                                    vl["address"]=tag.addr
                                    vl["status"]=tag.status
                                    vl["value"]=farms.get(k).getValueShort(v)
                                    fr["values"].append(vl)
         
            context["farms"].append(fr)   


    return templates.TemplateResponse("farminfo.html",context) 
    


#------------------------------------------------------
#/farm/all
#------------------------------------------------------
@app.get("/farm/all")
async def allfarminfo(farms: FarmList = Depends(get_farm_list)):
    """возвращает считаные законфигурированные значения  параметров фермы в виде списка json """
    ret=[]
    for k in farms.farms:
        fr={}
        fr["id"]=k
        fr["name"]=farms.get(k).name
        fr["connection"]=farms.get(k).connectionstatus
        vl={}
        for v in farms.get(k).Value:
                vl[farms.get(k).getTagByShort(v).name]=farms.get(k).getValueShort(v)
        fr["values"]=vl  
        ret.append(fr)             
    return {"allfarms":ret}

#------------------------------------------------------
#/farm/{name}
#------------------------------------------------------
@app.get("/farm/{name}")
async def farminfo(name:str,farms: FarmList = Depends(get_farm_list)):
    """возвращает считаные законфигурированные значения  параметров фермы в виде списка json"""
    if farms.get_by_name(name):
            fr={}
            fr["id"]=farms.get_by_name(name).jconf["id"]
            fr["name"]=farms.get_by_name(name).name
            fr["connection"]=farms.get_by_name(name).connectionstatus
            vl={}
            for v in farms.get_by_name(name).Value:
                 vl[farms.get_by_name(name).getTagByShort(v).name]=farms.get_by_name(name).getTagByShort(v).get_dict()
            fr["values"]=vl            
            return {"farm":fr}
    else:
        raise HTTPException(
             status_code=404,
             detail=f"Farm '{name}' not found"
        )
#------------------------------------------------------
#/point/{id}
#------------------------------------------------------
@app.get("/point/{id}")
async def gettagbybase(id:str,farms: FarmList = Depends(get_farm_list)):
    """возвращает точку по ее id. на выходе набор параметров структуры  PointTag"""
    tag:PointTag=None
    for f in farms.farms:
        if farms.get(f).getTagByBaseId(id):
            tag=farms.get(f).getTagByBaseId(id)          
    if  tag==None:
        raise HTTPException(
            status_code=404,
            detail=f"Point '{id}' not found"
            )
    return tag
#------------------------------------------------------
#/sql/{id}
#------------------------------------------------------
    
@app.get("/sql/{id}")
async def sqltest(id:str,farms: FarmList = Depends(get_farm_list)):
    """возвращает строку sql для добавления тренда определенной точки """
    for f in farms.farms:
        if farms.get(f).getTagByBaseId(id):
            return farms.get(f).getTagByBaseId(id).get_sql_string()          
    return {"error":"not found"}
#------------------------------------------------------
#/browse/{id}/{node}
#------------------------------------------------------
@app.get("/browse/{id}/{node}")
async def browsetag(id:str, node:str,farms: FarmList = Depends(get_farm_list)):
    """Браузер дочерних нодов {node} на заданном обьекте ID """
    farm=farms.get_by_name(id)
    if not farm:
        raise HTTPException(
                    status_code=404,
                    detail=f"farm '{id}' not found"
                    )
    if node=='root':
       bufnode=farm.client.nodes.root

    else:
        bufnode=farm.client.get_node(node)
    if not bufnode:
        raise HTTPException(
                    status_code=404,
                    detail=f"node '{node}' not found"
                    )
    
    res=await farm.browse_nodes(node=bufnode,level=0, maxbrowselevel=0)
    return   {
           'strchildren':res['strchildren']

    }
#------------------------------------------------------
#/hbrowse/{id}/{node}
#------------------------------------------------------
@app.get("/hbrowse/{id}/{node}")
async def hbrowsetag(request:Request,id:str, node:str,farms: FarmList = Depends(get_farm_list)):
    """Браузер дочерних нодов {node} на заданном обьекте ID в виде ccaлок HTML"""
    context = {'request':request, "points":{}}
    farm=farms.get_by_name(id)
    if not farm:
        raise HTTPException(
                    status_code=404,
                    detail=f"farm '{id}' not found"
                    )
    if node=='root':
       bufnode=farm.client.nodes.root

    else:
        bufnode=farm.client.get_node(node)
    if not bufnode:
        raise HTTPException(
                    status_code=404,
                    detail=f"node '{node}' not found"
                    )

    res=await farm.browse_nodes(node=bufnode,level=0, maxbrowselevel=0)
    context["farm"]=id
   # for child in res['strchildren']:
   #     context["points"].append(child)
    context["points"]=res['typedict']
    return templates.TemplateResponse("farmbrowse.html",context) 
#------------------------------------------------------
#/hbrowse/{id}/{node}
#------------------------------------------------------
   
@app.post("/write/{baseid}/{value}")
async def writeval( baseid:str,value:str,auth:Union[str, None]= Header(default=None,alias="Auth"),farms: FarmList = Depends(get_farm_list)):
    """Запись значения точки по ее BaseID"""
    if not ((baseid==None) or  (value==None)):
        for f in farms:
            point=farms.get(f).getTagByBaseId(baseid)
            if point:
                result =await farms.get(f).WriteValueShort(point.addr,value)
                return {
                        "result":result,
                        "detail":f"{'Write sucesfull' if result  else 'Write failed'}",
                        "id":str(baseid),
                        "value":str(value),
                        "Authorization":auth
                        }
    raise HTTPException(
                        status_code=404,
                        detail=f"Point '{baseid}' not found"
                        )
