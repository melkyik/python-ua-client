
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

ic.disable()
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
file_handler = RotatingFileHandler("/var/scripts/python-ua-client/mixings.log", maxBytes=50000, backupCount=10,encoding="UTF8")
file_handler.setLevel(logging.INFO)

# Create a formatter for the main module file handler
formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
file_handler.setFormatter(formatter)
mylogger.addHandler(file_handler)
logging.getLogger("FarmClass").addHandler(file_handler)
#---------------------------------
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





    
WORK_DIR='/var/scripts/python-ua-client/getmix_config'
farms=FarmList()
def setup():
    """читает данные всех ферм"""
    settings=[]  

    #ic.disable() 
    files:list[str]= os.listdir(WORK_DIR)
    for file_name in files:
        file_path = os.path.join(WORK_DIR, file_name)
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
    files:list[str]= os.listdir(WORK_DIR)
    for file_name in files:
        file_path = os.path.join(WORK_DIR, file_name)
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
            pt+=tempfu.get_values("mixdata")
            pt+=tempfu.get_values("recipedata")
            pt+=tempfu.get_values("values")
            #ic(pt)
            names,points=zip(*pt)
                
            

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
                
                farms.get(i).bd_logfilter=tempfu.get("logfilter") if tempfu.get("logfilter") else None
     
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
#                    ic(shortpoint)
        except KeyError as error: #ловушка на некорректную конфу в базе
            mylogger.warning(f"Косяк в конфе фермы  {k[0]}, глюк в поле {error}" )
        finally:
            del tempSQL,tempfu
      
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


async def mix_loop():
    def to_int(x)->int:
        return 0 if (x is None) or (x=="None") else int(float(x))
    oldautostage=0
    start_date:datetime=None
    while True:
       
        f=farms["1"]
        auto,autostat= to_int(f.getValueShort("GVL.Command.AutoStage")),f.getTagByShort("GVL.Command.AutoStage").status,
        recipe= to_int(f.getValueShort("GVL.Command.Automate.Recipe"))
        autostage,plcdate= to_int(f.getValueShort("GVL.Command.Automate.Stage")),f.getTagByShort("GVL.Command.Automate.Stage").plcdate
        if oldautostage!=autostage:
            mylogger.info(f"autostage ={autostage} old={oldautostage} ")
        if (auto==1) and autostat: #автоматический режим активен
            if (oldautostage !=autostage ) and (autostage in range(3,5)): #начат замес
                mylogger.info(f"{f.name} - зафиксирован старт замеса в {plcdate}")
                start_date=plcdate
            if (oldautostage in range(5,9)) and (autostage==9): #значит начат залив в зону
                mylogger.info(f"{f.name} - зафиксирован залив в зону {recipe} в {plcdate}")
                url_object = URL.create(
                    "mysql+pymysql",
                    username="scadauser",
                    password="3a8AWur6H2",  # plain (unescaped) text
                    host="10.10.0.251",
                    database="testdemo",
                )
                try:
                    if f.getTagByShort("GVL.Command.AutoStage").status:
                        engine= create_engine(url_object,echo=True)
                        Session=sessionmaker(bind=engine)
                        session=Session()
                        if (start_date=="None") or (start_date is None):
                            start_date=plcdate
                        row=MixData(        farm=f.name,
                                            start_mix=start_date,
                                            end_mix=plcdate,
                                            result=None,
                                            zone=recipe,
                                            rd_Automate         =f.getPointByName(f"recipedata[{recipe}].Automate").value,
                                            rd_AutomateCorr     =f.getPointByName(f"recipedata[{recipe}].AutomateCorr").value,
                                            rd_Cycle            =f.getPointByName(f"recipedata[{recipe}].Cycle").value,
                                            rd_nCycle           =f.getPointByName(f"recipedata[{recipe}].nCycle").value,
                                            rd_K                =f.getPointByName(f"recipedata[{recipe}].K").value,
                                            rd_KEC              =f.getPointByName(f"recipedata[{recipe}].KEC").value,
                                            rd_KpH              =f.getPointByName(f"recipedata[{recipe}].KpH").value,
                                            rd_V_irrigation     =f.getPointByName(f"recipedata[{recipe}].K").value,
                                            rd_DoseZone_0       =f.getPointByName(f"recipedata[{recipe}].DoseZone[0]").value,
                                            rd_DoseZone_1       =f.getPointByName(f"recipedata[{recipe}].DoseZone[1]").value,
                                            rd_DoseZone_2       =f.getPointByName(f"recipedata[{recipe}].DoseZone[2]").value,
                                            rd_DoseZone_3       =f.getPointByName(f"recipedata[{recipe}].DoseZone[3]").value,
                                            rd_DoseZone_4       =f.getPointByName(f"recipedata[{recipe}].DoseZone[4]").value,
                                            rd_DoseZone_5       =f.getPointByName(f"recipedata[{recipe}].DoseZone[5]").value,
                                            rd_DoseZone_6       =f.getPointByName(f"recipedata[{recipe}].DoseZone[6]").value,
                                            rd_DoseZone_7       =f.getPointByName(f"recipedata[{recipe}].DoseZone[7]").value,
                                            rd_DoseZone_8       =f.getPointByName(f"recipedata[{recipe}].DoseZone[8]").value,
                                            rd_DoseZone_9       =f.getPointByName(f"recipedata[{recipe}].DoseZone[9]").value,
                                            
                                            rd_EC_After_0       =f.getPointByName(f"recipedata[{recipe}].EC_After[0]").value,
                                            rd_EC_After_1       =f.getPointByName(f"recipedata[{recipe}].EC_After[1]").value,
                                            rd_EC_After_2       =f.getPointByName(f"recipedata[{recipe}].EC_After[2]").value,
                                            rd_EC_After_3       =f.getPointByName(f"recipedata[{recipe}].EC_After[3]").value,
                                            rd_EC_After_4       =f.getPointByName(f"recipedata[{recipe}].EC_After[4]").value,
                                            rd_EC_After_5       =f.getPointByName(f"recipedata[{recipe}].EC_After[5]").value,
                                            rd_EC_After_6       =f.getPointByName(f"recipedata[{recipe}].EC_After[6]").value,
                                            rd_EC_After_7       =f.getPointByName(f"recipedata[{recipe}].EC_After[7]").value,
                                            rd_EC_After_8       =f.getPointByName(f"recipedata[{recipe}].EC_After[8]").value,
                                            rd_EC_After_9       =f.getPointByName(f"recipedata[{recipe}].EC_After[9]").value,
                                            md_ECr_0            =None,
                                            md_ECr_1            =f.getPointByName(f"mixdata.ECr[1]").value,
                                            md_ECr_2            =f.getPointByName(f"mixdata.ECr[2]").value,
                                            md_ECr_3            =f.getPointByName(f"mixdata.ECr[3]").value,
                                            md_ECr_4            =f.getPointByName(f"mixdata.ECr[4]").value,
                                            md_ECr_5            =f.getPointByName(f"mixdata.ECr[5]").value,
                                            md_ECr_6            =f.getPointByName(f"mixdata.ECr[6]").value,
                                            md_ECr_7            =f.getPointByName(f"mixdata.ECr[7]").value,
                                            md_ECr_8            =f.getPointByName(f"mixdata.ECr[8]").value,
                                            md_ECr_9            =f.getPointByName(f"mixdata.ECr[9]").value,
                                            md_dozevol_0        =None,
                                            md_dozevol_1        =f.getPointByName(f"mixdata.dozevol[1]").value,
                                            md_dozevol_2        =f.getPointByName(f"mixdata.dozevol[2]").value,
                                            md_dozevol_3        =f.getPointByName(f"mixdata.dozevol[3]").value,
                                            md_dozevol_4        =f.getPointByName(f"mixdata.dozevol[4]").value,
                                            md_dozevol_5        =f.getPointByName(f"mixdata.dozevol[5]").value,
                                            md_dozevol_6        =f.getPointByName(f"mixdata.dozevol[6]").value,
                                            md_dozevol_7        =f.getPointByName(f"mixdata.dozevol[7]").value,
                                            md_dozevol_8        =f.getPointByName(f"mixdata.dozevol[8]").value,
                                            md_dozevol_9        =f.getPointByName(f"mixdata.dozevol[9]").value,
                                            md_Dosername_0      =None,
                                            md_Dosername_1      =f.getPointByName(f"mixdata.dosernames[1]").value,
                                            md_Dosername_2      =f.getPointByName(f"mixdata.dosernames[2]").value,
                                            md_Dosername_3      =f.getPointByName(f"mixdata.dosernames[3]").value,
                                            md_Dosername_4      =f.getPointByName(f"mixdata.dosernames[4]").value,
                                            md_Dosername_5      =f.getPointByName(f"mixdata.dosernames[5]").value,
                                            md_Dosername_6      =f.getPointByName(f"mixdata.dosernames[6]").value,
                                            md_Dosername_7      =f.getPointByName(f"mixdata.dosernames[7]").value,
                                            md_Dosername_8      =f.getPointByName(f"mixdata.dosernames[8]").value,
                                            md_Dosername_9      =f.getPointByName(f"mixdata.dosernames[9]").value,
                                            md_pHmix=None,
                                            md_ECmix=None,
                                                    )
                        


                        session.add(row)
                        session.commit()
                        session.close()
                        mylogger.info(f"row added {row}")
                except() as error:
                    mylogger.error(error)
        oldautostage=autostage
        await asyncio.sleep(1)



async def print_farm_loop():
    while True:
        await aioconsole.ainput()     
        farms["1"].PrintValues(points=farms["1"].get_filtered_list_of_shorts("mixdata"))





async def main():
    try:
        tasks=[]
   

        

        for k in farms:
             tasks.append(asyncio.create_task(farms.get(k).loop()))
        #tasks.append(asyncio.create_task(AppStatus.terminate()))
        #tasks.append(asyncio.create_task(trends_loop()))
        #await server.serve()
        #tasks.append(asyncio.create_task(print_farm_loop())) #для тестирования обмена с OPC
        tasks.append(asyncio.create_task( mix_loop()))
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
  
   


