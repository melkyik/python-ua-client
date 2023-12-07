
#будем тут собирать данные по замесам
from icecream import ic
import json
import asyncio
import os
import logging
import copy
from typing import Any
from logging.handlers import RotatingFileHandler
from FarmClass import FarmPLC,FarmList,PointTag,extract_point_name,BrowseDict
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
file_handler = RotatingFileHandler("mixings.log", maxBytes=50000, backupCount=10,encoding="UTF8")
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
    #распаковка дозаторов в рецептах
    buf["plcip"][funit]["recipedata"]=[expand_list(i,"%DOSER%",(int(fu["dosers_range"][0]), int(fu["dosers_range"][1]))) for i in buf["plcip"][funit]["recipedata"]]
    #распаковка дозаторов в разделе mixdata
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

if __name__=="__main__":
    configlist= setup()
    #распаковка  по префиксу REC чтобы создался список со словарем в recipedata
    fu1=BrowseDict(getfu(configlist[0],"FU1"))
    ic(fu1)
    ic(fu1.get_child("recipedata[0].Automate"))
    ic(fu1.find_substring_path("RecipesStruct.Recipes[1].Automate")[0])

    #ic(find_substring_path(fu1,".EC_After"))
  
   


