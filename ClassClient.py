
from prettytable import PrettyTable
import logging
import json
from FarmClass import FarmPLC
import asyncio

farms=dict()
f=[]
c=1

def fr(s)->FarmPLC:
        try:
        #транслятор указателя в тип FarmPLC для удобства кода и спелчека 
         if isinstance(farms[str(s)],FarmPLC):
                return farms[str(s)]
        except(KeyError):
                return None


with open("config.json", "r") as read_file: #читаем файл с конфигурации и делаем из него фермы
        config = json.load(read_file)

for k in config["device"]:      #создание экземпляров обьектов ферм
   farms[k["id"]]=FarmPLC(jconf=k)


async def printfarms(): #процедурка для вывода считаных значений и записи переменных
         global c
         while True:
            c=c+1
            #print("\033c", end='') 
            fr(1).PrintValues() 
            fr(2).PrintValues()
            await fr(1).WriteValueShort("GVL.AIArray.AI[0].AIData.Value",c)  
            print(c)
            await asyncio.sleep(1)    

async def main():
        tasks=[]
        for k in farms:
                tasks.append(asyncio.create_task(fr(k).loop()))
        tasks.append(asyncio.create_task(printfarms()))
        await asyncio.gather(*tasks)

        
#logging.basicConfig(level=logging.INFO) 

if __name__ == "__main__":
        asyncio.run(main())

#https://stackoverflow.com/questions/31623194/asyncio-two-loops-for-different-i-o-tasks
