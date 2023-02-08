
import asyncpg
import json
import asyncio
import logging
from FarmClass import FarmPLC,FarmList
import uvicorn
from fastapi import FastAPI,Request
from uvicorn.main import Server
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi.responses import HTMLResponse

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
                     print("Task cancelled")
            await asyncio.sleep(0.1)
Server.handle_exit = AppStatus.handle_exit

#https://coderoad.ru/58133694/%D0%93%D1%80%D0%B0%D0%BC%D0%BE%D1%82%D0%BD%D0%BE%D0%B5-%D0%BE%D1%82%D0%BA%D0%BB%D1%8E%D1%87%D0%B5%D0%BD%D0%B8%D0%B5-uvicorn-starlette-app-%D1%81-websockets
#https://stackoverflow.com/questions/56052748/python-asyncio-task-cancellation
####=====================
#веб сервак
#================
app=FastAPI()
templates=Jinja2Templates(directory="static")
app.mount("/static", StaticFiles(directory="static"), name="static")

@app.get("/",response_class=HTMLResponse )
async def index(request:Request):
    context = {'request':request}
    return templates.TemplateResponse("farminfo.html",context) 


@app.get("/")
async def root():
    return {"message": "Hello World"}
    

@app.get("/farm/all")
async def allfarminfo():
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

@app.get("/farm/{name}")
async def farminfo(name:str):
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
        return {"error":"not found"}
@app.get("/point/{id}")
async def gettagbybase(id:str):
            for f in farms.farms:
                if farms.get(f).getTagByBaseId(id):
                    return farms.get(f).getTagByBaseId(id)          
            return {"error":"not found"}
@app.get("/sql/{id}")
async def sqltest(id:str):
            for f in farms.farms:
                if farms.get(f).getTagByBaseId(id):
                    return farms.get(f).getTagByBaseId(id).get_sql_string()          
            return {"error":"not found"}







logging.basicConfig(level=logging.WARNING,
                        format="%(asctime)s: %(message)s",
                        datefmt=  '%Y-%m-%d %H:%M:%S')  
mylogger = logging.getLogger("ifarm")

setupfarms:bool=False
farms=FarmList("Список ферм из базы")
"""Список ферм класc FarmList"""
class ifarmPgSql: 
    """класс определяет подключение к субд PostgreSql"""
    def __init__(self) -> None:
        pass
    async def connect(self):
         # Подключение к существующей базе данных
        self._connection= await asyncpg.connect(user="igor",
                                        # пароль, который указали при установке PostgreSQL
                                        password="adminsa",
                                        host="10.10.2.152",
                                        port="5432",
                                        database="ifarm")
        self.conn:asyncpg.connection.Connection = self._connection
              
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

        
def extract_point_name(s)->list:
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
            print(f"Ферма {k['title']} {len(points)} точек")
            #print(points)
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
                    print(shortpoint)
        except KeyError as error: #ловушка на некорректную конфу в базе
            mylogger.warning(f"косяк в конфе фермы  {k[0]}, глюк в поле {error}" )
      
    print("сумма активных ферм:",len(farms.farms))
   
    return True


async def printfarms(): 
        global farms
        """процедурка для вывода считаных значений и записи переменных"""
        while True:
            print("\033c", end='') 
            for k in farms.farms:
              farms.get(k).PrintValues()
            #await fr(1).WriteValueShort("GVL.AIArray.AI[0].AIData.Value",c)  
            await asyncio.sleep(1)     
async def trends_loop():
    while True:
        await asyncio.sleep(60) 
         # Подключение к существующей базе данных
        connection=await asyncpg.connect(user="igor",
                                        # пароль, который указали при установке PostgreSQL
                                        password="adminsa",
                                        host="10.10.2.152",
                                        port="5432",
                                        database="ifarm_scada")  
        conn:asyncpg.connection.Connection = connection
        
        q=farms.generate_trends()
        print(q)
        await conn.execute(q)
     
       
        await conn.close()

async def setups():
    
        await base.connect() 
        await setup()
        await base.close() 
config = uvicorn.Config(app, port=8000, log_level="info")
server = uvicorn.Server(config) 

async def main():
 
        tasks=[]
        await setups()
        tasks.append(asyncio.create_task(trends_loop()))

        for k in farms.farms:
              tasks.append(asyncio.create_task(farms.get(k).loop()))
        tasks.append(asyncio.create_task(AppStatus.terminate()))
        await server.serve()
        await asyncio.gather(*tasks)
       
       # tasks.append(asyncio.create_task(printfarms()))

if __name__ == "__main__":           

    asyncio.run(main())   

  
  
        
    
    