
from prettytable import PrettyTable
import logging
import json
from FarmClass import FarmPLC
import asyncio

farms=dict()

with open("config.json", "r") as read_file: 
        config = json.load(read_file)

for k in config["device"]:
    farms[k["id"]]=FarmPLC(jconf=k)
   #print(str(farms[k["id"]]))


async def main():

        #tasks.append(asyncio.create_task(farms["1"].loop()))
        #tasks.append(asyncio.create_task(farms["2"].loop()))
        await asyncio.gather(
        asyncio.create_task(farms["1"].loop()),
        asyncio.create_task(farms["2"].loop())
        )
        await asyncio.sleep(1)
#logging.basicConfig(level=logging.INFO) 
#print("\033c", end='') 
#print (farms["1"].nodes_to_read)
asyncio.run(main())
#asyncio.run(farms["2"].loop())
#https://stackoverflow.com/questions/31623194/asyncio-two-loops-for-different-i-o-tasks
