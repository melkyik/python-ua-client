import json
from asyncua import Client, ua, Node
import logging
import asyncio

class FarmPLC: #чтоб сьел субхандлер
    Values            =  {} #сопоставление адреса и текущего значения

class SubHandler:
    def datachange_notification(self, farm: FarmPLC, node: Node, val, data):
        farm.Values[node.nodeid]=val
         # called for every datachange notification from server
        #_logger.info("datachange_notification %r %s", node, val)
    def event_notification(self, event: ua.EventNotificationList):
       #called for every event notification from server
            pass
    def status_change_notification(self, status: ua.StatusChangeNotification):
        #called for every status change notification from server
       # _logger.info("status_notification %s", status)
            pass




class FarmPLC(FarmPLC):
    Values            =  {} #сопоставление адреса и текущего значения
    handler = SubHandler()
    #при инициализации скармливаем распакованый словарь из файла конфигурации json с нужными данными
    def __init__(self,jconf={ "id":"1",
      "name":"PLC default",
      "URL":"opc.tcp://10.10.2.244:4840",
      "login":"admin",
      "password":"wago",
      "prefix":"ns=4;s=|var|WAGO 750-8212 PFC200 G2 2ETH RS.Application."},log=False):
      #инициализация и заполнение первичными данными из конфигурационного файла
      self.jconf    =           jconf
      self.prefix   =           jconf["prefix"]
      self.name     =           jconf["name"]
      self.URL      =           jconf["URL"]
      self.connection =         "init"
      self.SubscribeNodes    =  list() #список точек для подписки, остальные опрашиваются по общему опросу
      self.Nodes_To_read     =  list() #преобразованый список подписки для передачи в хендлер
      self.Values            =  {} #сопоставление адреса и текущего значения
    
      #загружаем стандартные точки из файла, для дополнительных надо чтото придумать... =(
      with open("standartpoints.json", "r") as read_file: 
        self.pointsdata = json.load(read_file)
      for p in self.pointsdata['Tag']:
        s=self.prefix+p["address"]
        self.SubscribeNodes.append(s)
        self.Values[s] = ""

    def getvalueshort(self,short)->str: 
        #возращает значение сохраненое в основном цикле
        return self.Values[self.prefix+short]

      
    def  __str__(self)->str:
        return f"{self.name} {self.URL}"
    


    async def loop(self):
        while True:
            self.client   =   Client(url=self.URL)
            self.client.set_user(self.jconf["login"])
            self.client.set_password(self.jconf["password"])
            try:
                async with self.client:
                    self.connection("Connected")
                    self.subscription = await self.client.create_subscription(500, self.handler)
    
                self.nodes_to_read = [Node(self.client, n) for n in self.SubscribeNodes]
               
                await self.subscription.subscribe_data_change(self.nodes_to_read)
         
                while True:
                    await asyncio.sleep(1)
                    await client.check_connection()  # Throws a exception if connection is lost
            except (ConnectionError, ua.UaError):
               #_logger.warning("Reconnecting in 2 seconds")
                await asyncio.sleep(2)


if __name__ == "__main__":

    logging.basicConfig(level=logging.INFO)
    asyncio.run(main())
