
from prettytable import PrettyTable
import logging
import json
from FarmClass import FarmPLC
import asyncio

farms=dict()
c=1

with open("config.json", "r") as read_file: 
        config = json.load(read_file)

for k in config["device"]:
   farms[k["id"]]=FarmPLC(jconf=k)
   #print(str(farms[k["id"]]))


async def printfarms():
         global c
         while True:
            c=c+1
            #print("\033c", end='') 
            farms["1"].PrintValues() 
            farms["2"].PrintValues()
            #await farms["1"].WriteValueShort("GVL.AIArray.AI[0].AIData.RawOverflow",c)  
            print(c)
            await asyncio.sleep(1)    
                
async def writeval():
        global c
           

async def main():
      
        tasks=[]
        for k in farms:
                tasks.append(asyncio.create_task(farms[k].loop()))
        tasks.append(asyncio.create_task(printfarms()))
       # tasks.append(writeval())
        await asyncio.gather(*tasks)

        
#logging.basicConfig(level=logging.INFO) 

if __name__ == "__main__":
        asyncio.run(main())

#https://stackoverflow.com/questions/31623194/asyncio-two-loops-for-different-i-o-tasks
