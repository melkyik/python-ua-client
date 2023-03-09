
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
from typing import Optional,Union,List



original_handler = Server.handle_exit

class AppStatus:
    should_exit = False

    @staticmethod
    def handle_exit(*args, **kwargs):
        AppStatus.should_exit = True
        original_handler(*args, **kwargs)
    @staticmethod
    async def terminate(): #для остановки всех процессов ASYNC после выключения веб сервера

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
templates=Jinja2Templates(directory="static")
app.mount("/static", StaticFiles(directory="static"), name="static")

@app.get("/",response_class=HTMLResponse )
async def index(request:Request):
    context = {'request':request, "farms":[]}
    for k in farms.farms:
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
async def allfarminfo():
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
async def farminfo(name:str):
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
async def gettagbybase(id:str):
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
async def sqltest(id:str):
    """возвращает строку sql для добавления тренда определенной точки """
    for f in farms.farms:
        if farms.get(f).getTagByBaseId(id):
            return farms.get(f).getTagByBaseId(id).get_sql_string()          
    return {"error":"not found"}
#------------------------------------------------------
#/browse/{id}/{node}
#------------------------------------------------------
@app.get("/browse/{id}/{node}")
async def browsetag(id:str, node:str):
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
async def hbrowsetag(request:Request,id:str, node:str):
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
async def writeval( baseid:str,value:str,auth:Union[str, None]= Header(default=None,alias="Auth")):
    """Запись значения точки по ее BaseID"""
    if not ((baseid==None) or  (value==None)):
        for f in farms.farms:
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

#---------------------------------
##настройка логгера
#---------------------------------
logging.basicConfig(level=logging.INFO,
                        format="%(name)s - %(levelname)s - %(message)s",
                        datefmt=  '%Y-%m-%d %H:%M:%S')  
mylogger = logging.getLogger(__name__)

# Create a file handler for the main module logger
file_handler = RotatingFileHandler("main.log", maxBytes=50000, backupCount=10,encoding="UTF8")
file_handler.setLevel(logging.INFO)

# Create a formatter for the main module file handler
formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
file_handler.setFormatter(formatter)
mylogger.addHandler(file_handler)
logging.getLogger("FarmClass").addHandler(file_handler)


setupfarms:bool=False
farms=FarmList("Список ферм из базы")
"""Список ферм класc FarmList"""
class ifarmPgSql: 
    """класс определяет подключение к субд PostgreSql"""
    def __init__(self) -> None:
        pass
    async def connect(self):
         # Подключение к существующей базе данных
        self._connection= await asyncpg.connect(user="sc",
                                        # пароль, который указали при установке PostgreSQL
                                        password="MIO54jklw2",
                                        host="3.69.35.190",
                                        port="5432",
                                        database="sc")
        self.conn:asyncpg.connection.Connection = self._connection
        mylogger.info("Соединение с PostgreSQL установлено")      
#--------------------------------------------------------
    async def close(self):   
            """разрыв соединения"""  
            if self.conn:
                mylogger.info("Соединение с PostgreSQL закрыто")
                await self.conn.close()
#--------------------------------------------------------                
    async def get_farm_settings(self)->list:
        """считывание параметров связи для фермы""" 
      
        if self.conn:
                query= "SELECt title,settings \
                FROM scada_settings "
                s=await self.conn.fetch(query) 
   
        return s
#--------------------------------------------------------    
    async def getpointsforfarm(self,farm)->list:
        """считывание списка точек, где 1 позиция  - identity имя точки, 2 позиция title описание"""
        if self.conn:
                query= f"SELECT identity,scada_sensors.title stitle,\
						scada_settings.title ftitle,\
                        scada_sensors.id, scada_sensors.display_graphs\
                        FROM public.scada_sensors \
                        inner join scada on scada_id=scada.id \
                        inner join scada_settings on setting_id=scada_settings.id\
                        WHERE scada_sensors.status='active'\
						and scada.status='active'\
                  		and scada_settings.title ='{farm}'\
						order by scada_sensors.identity asc\
                            ;"
                
                s=await self.conn.fetch(query)
           
        return s

        
def extract_point_name(s:str)->list:
    """считывает имя точки и парсит его на составляющие - префиксы и имя"""
    try:

        if s.find('RS.Application.'):
            return s[s.find('RS.Application.')+15:],s[s.find("|var|"):s.find('RS.Application.')+15],"ns=4;s="
        else:
            return [s,'','']
    except:
        return [s,'','']




base=ifarmPgSql()
"""создает класс работы с базой"""
async def setup():

    """читает данные всех ферм"""
    settings=await base.get_farm_settings() #читаем фермы с базы
   # print(settings)
    i=0

    for k in settings:     #создание экземпляров обьектов ферм по списку            
        j= json.loads(k["settings"])
        js= json.loads(j) #хз почему но первый вызов делает на выходе строку а второй только конвертит в словарь!
        try:
            points=await base.getpointsforfarm(k["title"]) #считаем список точек для этой фермы
            mylogger.info(f"Ферма {k['title']} {len(points)} точек")
            if points!=[]:
                i+=1
                farms.add(   #вызов конструктора
                jconf={ "id":str(i),
                "name":k[0],
                "URL":f"opc.tcp://{js['opcEndpoint']['host']}:4840",
                "login":f"{js['opcEndpoint']['security']['userName']}",
                "password":f"{js['opcEndpoint']['security']['password']}",
                "prefix":"ns=4;s=",
                "retprefix":f"{extract_point_name(points[0]['identity'])[1] if points !=[] else ''}" #с 1 точки заберем префиксы для этого точки читаются выше
                 }
                )
                for p in points:
                    shortpoint=extract_point_name(p['identity'])[0],p['stitle'],str(p['id']),p['display_graphs']
                    farms.get(i).addpoint(shortpoint)   
                           #добавление точек в подписку и конфигурации
                   # print(shortpoint)
        except KeyError as error: #ловушка на некорректную конфу в базе
            mylogger.warning(f"Косяк в конфе фермы  {k[0]}, глюк в поле {error}" )
      
    mylogger.info("сумма активных ферм: %s",len(farms.farms.keys()))
   
    return True



async def trends_loop():
    while True:
        await asyncio.sleep(60) 
         # Подключение к существующей базе данных
        connection=await asyncpg.connect(user="python_scada",
                                        # пароль, который указали при установке PostgreSQL
                                        password="J)DSWj3",
                                        host="3.72.44.203",
                                        port="5432",
                                        database="python_scada")  
        conn:asyncpg.connection.Connection = connection
        
        q=farms.generate_trends()
        mylogger.info("Trend writed") 
        await conn.execute(q)
        await conn.execute(''' COMMIT''')    
        await conn.close()

async def setups():
    
        await base.connect() 
        await setup()
        await base.close() 
config = uvicorn.Config(app, host='0.0.0.0', port=8000, log_level="warning")
server = uvicorn.Server(config) 

async def main():
    try:
        tasks=[]
        await setups()
        

        for k in farms.farms:
             tasks.append(asyncio.create_task(farms.get(k).loop()))
        tasks.append(asyncio.create_task(AppStatus.terminate()))
        tasks.append(asyncio.create_task(trends_loop()))
        await server.serve()
        await asyncio.gather(*tasks)
    except asyncio.exceptions.CancelledError:
         mylogger.info("exit by cancel") 
         return 0  

if __name__ == "__main__":           

    asyncio.run(main())   

  
  
        
    
    
