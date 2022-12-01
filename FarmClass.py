import json
from asyncua import Client, ua, Node
import logging
import asyncio
from prettytable import PrettyTable

#_logger = logging.getLogger(__name__)
class SubHandler:
    Value           =  {} #сопоставление адреса и текущего значения
    datachanged     = False
    def datachange_notification(self, node: Node, val, data):
         # called for every datachange notification from server
        #_logger.info("datachange_notification %r %s", node, val)
        #переводим в строку тк node.nodeid.Identifier возвратит будет только часть имени в словаре типа 
        # например |var|WAGO 750-8212 PFC200 G2 2ETH RS.Application.PLC_PRG.counter
        self.Value[str(node.nodeid.Identifier)]=val
        self.datachanged=True
        #print(val)
        
    def event_notification(self, event: ua.EventNotificationList):
       #called for every event notification from server
        pass
    def status_change_notification(self, status: ua.StatusChangeNotification):
        #called for every status change notification from server
       # _logger.info("status_notification %s", status)
        pass




class FarmPLC:
    Value            =  {} #сопоставление адреса и текущего значения, словарь текущих значений
    handler = SubHandler()
    #при инициализации скармливаем распакованый словарь из файла конфигурации json с нужными данными
    def __init__(self,jconf:dict={ "id":"1",
      "name":"PLC default",
      "URL":"opc.tcp://10.10.2.244:4840",
      "login":"admin",
      "password":"wago",
      "prefix":"ns=4;s=",
      "retprefix":"|var|WAGO 750-8212 PFC200 G2 2ETH RS.Application."
      },log=False):
      #инициализация и заполнение первичными данными из конфигурационного файла
   
      self.jconf    =           jconf.copy()
      print(self.jconf)
      self.prefix   =           self.jconf['prefix'] #префикс точек списка подписки
      self.retprefix   =        self.jconf['retprefix'] #префикс точек ответа подписки в ответе str(node.nodeid.Identifier)
                                                        #первые символы префикса "ns=4;s=" там отсуствуют
      self.name     =           self.jconf['name']  
      self.URL      =           self.jconf['URL']
      self.SubscribeNodes    =  list() #список точек для подписки, остальные опрашиваются по общему опросу
      #self.Nodes_To_read     =  list() #преобразованый список подписки для передачи в хендлер
      
    
      #загружаем стандартные точки из файла, для дополнительных надо чтото придумать... =(
      with open("standartpoints.json", "r") as read_file: 
        self.pointsdata = json.load(read_file)
      for p in self.pointsdata['Tag']:
        s=self.prefix+self.retprefix+p["address"]
        self.SubscribeNodes.append(s)
        self.Value[self.retprefix+s] = ""
        print (self.SubscribeNodes)
   

    def getvalueshort(self,short)->str: 
        #возращает значение сохраненое в основном цикле
        return str(self.Value[str(self.retprefix)+short])

      
    def  __str__(self)->str:
        #возвращает имя и url
        return f"{self.name} {self.URL}"
    
  
        



    async def loop(self):
        #метод для зацикливания
        while True:
            self.client   =   Client(url=self.URL)
            self.client.set_user(self.jconf["login"])
            self.client.set_password(self.jconf["password"])
            try:
                async with self.client:
                    self.subscription = await self.client.create_subscription(500, self.handler)
                    nodes_to_read = [Node(self.client, n) for n in self.SubscribeNodes]
                   # print(self.nodes_to_read)
                    await self.subscription.subscribe_data_change(nodes=nodes_to_read, 
                    attr=ua.AttributeIds.Value, 
                    queuesize=50, )
         
                    while True:
                        await asyncio.sleep(1)
                        if self.handler.datachanged:
                            self.value=self.handler.Value.copy()  # передаем копию считаных данных в значения
                            self.handler.datachanged=False
                            #for n in self.value: print(n,self.value[n], '\n ' )
                        await self.client.check_connection()  # Throws a exception if connection is lost
            except (ConnectionError, ua.UaError):
               #_logger.warning("Reconnecting in 2 seconds")
                await asyncio.sleep(2)

    


"""
if __name__ == "__main__":

    logging.basicConfig(level=logging.INFO)
    asyncio.run(main())
    """
