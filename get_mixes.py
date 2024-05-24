
#будем тут собирать данные по замесам
from icecream import ic
import json
import asyncio
import os
import logging
import copy
from typing import Any
import aioconsole
from logging.handlers import RotatingFileHandler
from FarmClass import FarmPLC,FarmList,PointTag,extract_point_name,BrowseDict,extract_prefix
from mixtableclass import MixData
import sqlalchemy
from sqlalchemy import URL,create_engine
from sqlalchemy.orm import sessionmaker
from datetime import datetime
from dotenv import load_dotenv
import os
from os.path import join, dirname
dotenv_path = join(dirname(__file__), '.env')
load_dotenv(dotenv_path)
farms=FarmList()

#---------------------------------
##настройка отладчика
#---------------------------------
#разремить если  нужна отладка 
#ic.disable() 
ic.configureOutput(includeContext=True) 
#---------------------------------
##настройка логгера
#---------------------------------
logging.basicConfig(level=logging.INFO,
                        format="%(name)s - %(levelname)s - %(message)s",
                        datefmt=  '%Y-%m-%d %H:%M:%S')  
mylogger = logging.getLogger(__name__)

# Создаем file handler for the main module logger
file_handler = RotatingFileHandler("/var/scripts/python-ua-client/logs/mixings.log", maxBytes=100000, backupCount=10,encoding="UTF8")
file_handler.setLevel(logging.INFO)

# Create a formatter for the main module file handler
formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
file_handler.setFormatter(formatter)
mylogger.addHandler(file_handler)
logging.getLogger("FarmClass").addHandler(file_handler)

#mylogger.info(os.getenv("TEST_ENV"))
#---------------------------------


farms=FarmList()
def setup():
    """читает данные всех ферм"""
    settings=[]  

    #ic.disable() 
    files:list[str]= os.listdir(os.environ.get("WORK_DIR"))
    for file_name in files:
        file_path = os.path.join(os.environ.get("WORK_DIR"), file_name)
        if os.path.isfile(file_path) and file_name.lower().endswith('.json') and not file_name.lower().__contains__('_'):
            try:
                with open(file_path, "r") as read_file: 
                    settings.append(json.load(read_file))
                   
            except:
                mylogger.error(f" cant read file {file_path}")
    return settings

def has_rec_keyword(value, keyword):
    """проверка условия что префикс есть в значении или подзначениях и с ним нужно работать"""
    if isinstance(value, str) and keyword in value:
        return True
    elif isinstance(value, dict):
        return any(has_rec_keyword(sub_value, keyword) for sub_value in value.values())
    elif isinstance(value, list):
        return any(has_rec_keyword(sub_value, keyword) for sub_value in value)
    return False  
 
def expand_list(j,keyword:str,rng=(0,2))->Any:
    if  isinstance(j, str) and has_rec_keyword(j, keyword):
       return [j.replace(keyword, str(i)) for i in range(rng[0], rng[1] + 1)]    
    
    if isinstance(j, dict) and has_rec_keyword(j, keyword):
        duplicated_dict = copy.deepcopy(j)
        for key, value in duplicated_dict.items():
            if isinstance(value, str) and keyword in value :
                duplicated_dict[key] = expand_list(value,keyword, rng)
            elif isinstance(value, dict) and has_rec_keyword(value, keyword):
                duplicated_dict[key] = []
                for _ in range(rng[0], rng[1] + 1):
                    new_dict = copy.deepcopy(value)
                    for sub_key, sub_value in new_dict.items():
                        if isinstance(sub_value, str) and keyword in sub_value:
                            new_dict[sub_key] = sub_value.replace(keyword, str(_))
                    duplicated_dict[key].append(new_dict)
            
        return duplicated_dict
    
    if  isinstance(j, list):
       return [expand_list(value,keyword, rng) for value in j]
    return j

def getfu(set:dict,funit:str)->dict:
    "распаковываем конфигурацию из словаря с префиксами"
    buf=copy.deepcopy(set)
    fu=buf["plcip"][funit]
    buf["plcip"][funit]=expand_list(fu,"%REC%",(int(fu["recipes_range"][0]), int(fu["recipes_range"][1])))
    #распаковка дозаторов в рецептах в первую очередь, будет список словарей recipedata
    buf["plcip"][funit]["recipedata"]=[expand_list(i,"%DOSER%",(int(fu["dosers_range"][0]), int(fu["dosers_range"][1]))) for i in buf["plcip"][funit]["recipedata"]]
    #распаковка дозаторов в разделе recipedata, в каждом словаре появляются списки дозаторов 
    #распаковка дозаторов в mixdata  будет список словарей recipedata
    md=buf["plcip"][funit]["mixdata"]
   
    buf["plcip"][funit]["mixdata"]=expand_list(md,"%DOSER%",(int(fu["dosers_range"][0]), int(fu["dosers_range"][1]))) 
    return buf["plcip"][funit]

def find_substring_path(data, substring):
    def search_path(current_data, current_path):
        if isinstance(current_data, dict):
            for key, value in current_data.items():
                new_path = f"{current_path}.{key}" if current_path else key
                result = search_path(value, new_path)
                if result:
                    return result
        elif isinstance(current_data, list):
            for i, item in enumerate(current_data):
                new_path = f"{current_path}[{i}]"
                result = search_path(item, new_path)
                if result:
                    return result
        elif isinstance(current_data, str) and substring in current_data:
            return current_path, current_data
        return None

    return search_path(data, "")



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
                mylogger.info(f"Ферма {k['farmname']} FU{fucnt} {k['timezone']} {len(points)} точек")
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


"""
        0 : Text := 'Pending';
        1,2 : Text := 'Dumping to sewer';
        3,4 : Text := 'Filling tank';
        5,6: Text := 'Mixing solution  for zone';
        7: Text := 'Correcting pH';
        8: text:= 'Waiting to drain from the zone';
        9 : Text := 'Pumpung to zone';
        20 : Text := 'End operation';
"""



async def print_farm_loop():
    while True:
        await aioconsole.ainput()     
        farms["1"].PrintValues(points=farms["1"].get_filtered_list_of_shorts("mixdata"))





async def main():
    try:
        tasks=[]
        for k in farms:
             tasks.append(asyncio.create_task(farms.get(k).loop()))
             tasks.append(asyncio.create_task(farms.get(k).mix_loop()))
        #tasks.append(asyncio.create_task(AppStatus.terminate()))
        #tasks.append(asyncio.create_task(trends_loop()))
        #await server.serve()
        #tasks.append(asyncio.create_task(print_farm_loop())) #для тестирования обмена с OPC
        
        await asyncio.gather(*tasks)

    except asyncio.exceptions.CancelledError:
         mylogger.info("exit by cancel") 
         return 0  



if __name__=="__main__":
    setup2()
    asyncio.run(main())
    #ic(str(farms["1"].get_filtered_list_of_names("")))
    #распаковка  по префиксу REC чтобы создался список со словарем в recipedata
    #fu1=BrowseDict(extract_prefix(configlist[0]["plcip"]["FU1"]))
   # fu1=BrowseDict(fu1.extract_prefix())
    #ic(fu1)
    #tv,w=zip(*fu1.get_values(nested=True,find_key="mixdata"))
  

    #ic(fu1.get_child("recipedata[0].Automate"))
    #ic(fu1.find_substring_path("RecipesStruct.Recipes[1].Automate")[0])
    #ic(find_substring_path(fu1,".EC_After"))
  
   


