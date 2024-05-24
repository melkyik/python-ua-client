import logging.handlers
from fastapi import FastAPI
from farmsapi import app,AppStatus
from FarmClass import FarmList,BrowseDict,extract_prefix,extract_point_name
from sqlalchemy import URL
import uvicorn
from uvicorn.main import Server
import asyncio
import copy
import logging
import os
import json
import farms_logger
from icecream import ic

mylogger = logging.getLogger(__name__)
mylogger.handlers.clear()
mylogger.addHandler(farms_logger.file_handler)
#mylogger.addHandler(farms_logger.console_handler)
#logging.getLogger("FarmClass").addHandler(farms_logger.file_handler)
farms_logger.init_handlers()



mylogger.info("start")

from dotenv import load_dotenv
from os.path import join, dirname
dotenv_path = join(dirname(__file__), '.env')
load_dotenv(dotenv_path)

farms=FarmList()
app.state.farms = farms


def setup2():
    settings=[]  
    files:list[str]= os.listdir(os.environ.get("WORK_DIR"))
    for file_name in files:
        file_path = os.path.join(os.environ.get("WORK_DIR"), file_name)
        if os.path.isfile(file_path) and file_name.lower().endswith('.json') and not file_name.lower().__contains__('_'):
            try:
                with open(file_path, "r") as read_file: 
                    settings.append(json.load(read_file))
                   
            except:
                mylogger.error(f" cant read file {file_path}")

   # settings=await base.get_farm_settings() #читаем фермы с базы
   # print(settings)
    i=0

    for k in settings:     #создание экземпляров обьектов ферм по списку 
        fucnt=0
        tempSQL=BrowseDict(k["scada"])
        for fu in k["plcip"]:
            fucnt+=1
            tempfu=BrowseDict(extract_prefix(k["plcip"][fu]))
           
            pt=[]
            pt+=tempfu.get_values("subs")
            #pt+=tempfu.get_values("mixdata")
            #pt+=tempfu.get_values("recipedata")
            pt+=tempfu.get_values("values")
            pt+=tempfu.get_values("ECtank")
            #ic(pt)
            names,points=zip(*pt)
            #ic(names  ) 
            

            try:  
                mylogger.info(f"Ферма {k['farmname']} FU{fucnt} {len(points)} точек")
                if points!=[]:
                    i+=1
                    farms.add(   #вызов конструктора фермы с необходимыми данными для подключения
                    jconf={ "id":str(i),
                    "name":f"{k['farmname']} FU{fucnt}",
                    "URL":tempfu['opcip'],
                    "login":tempfu['opcuser'],
                    "password":tempfu['opcpassword'],
                    "prefix":"ns=4;s=",
                    "retprefix":f"{extract_point_name(points[0])[1] if points !=[] else ''}" #с 1 точки заберем префиксы для этого точки читаются выше
                    }
                    )
                    farms.get(i).timezone=k['timezone']
                    
                    farms.get(i).bd_logfilter=tempfu.get("logfilter") if tempfu.get("logfilter") else None
                    farms.get(i).zonenames=copy.deepcopy(tempfu.get("zonenames"))
                    
                    if  tempSQL.get("dbhost")  and tempSQL.get("dbuser") and  tempSQL.get("dbpass") and  tempSQL.get("dbname"):
                        #если есть данные по подключению для удаленки и то создаем строку URL для алхимии 
                        farms.get(i).bd_URL= URL.create(
                                            "mysql+pymysql",
                                            username=tempSQL.get("dbuser"),
                                            password=tempSQL.get("dbpass"),  
                                            host    =tempSQL.get("dbhost"),
                                            database=tempSQL.get("dbname")
                                            )
                        #ic(farms.get(i).bd_URL)                
                        
                    for p in pt:
                        shortpoint=extract_point_name(p[1])[0],p[0],str(i),False
                        farms.get(i).addpoint(shortpoint)   
                            #добавление точек в подписку и конфигурации
                        #ic(shortpoint)
            except KeyError as error: #ловушка на некорректную конфу в базе
                mylogger.warning(f"Косяк в конфе фермы  {k[0]}, глюк в поле {error}" )
     
                
    del tempSQL,tempfu
    fr=[]            
    #for f in farms:
    #    fr.append(farms.get(f).name)  
    mylogger.info("сумма активных ферм: %s",len(farms.keys()))
   
    return True

config = uvicorn.Config(app, host='0.0.0.0', port=8001, log_level="warning")
server = uvicorn.Server(config) 
async def main():
    try:
        tasks=[]
        setup2()
        

        for k in farms:
             tasks.append(asyncio.create_task(farms.get(k).loop()))
        tasks.append(asyncio.create_task(AppStatus.terminate()))

        await server.serve()
        await asyncio.gather(*tasks)
    except asyncio.CancelledError:
         mylogger.info("exit by cancel") 
         return 0  

if __name__ == "__main__":           

    asyncio.run(main())   


