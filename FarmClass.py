import json
from asyncua import Client, ua, Node
import logging
import asyncio #https://github.com/FreeOpcUa/opcua-asyncio
from prettytable import PrettyTable

#_logger = logging.getLogger(__name__)
class SubHandler:
  
    def __init__(self):
        self.Value           =  {} #сопоставление адреса и текущего значения
        self.datachanged     = False
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


class NodePoint: 
    #в планах перевести точки в этот класс где будут хранится нужные параметры в том числе статус записи
    def __init__(self,name:str,retname:str,fullname:str,uatype:ua.VariantType):
        self.name=name
        self.retname=retname
        self.fullname=fullname
    
        pass

#--------------------------------------------------------
# класс экземпляров клиентов ферм
#--------------------------------------------------------
class FarmPLC:
      
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
      self.Value            =  {} #сопоставление адреса и текущего значения, словарь текущих значений
      self.jconf    =           jconf.copy()
      #print(self.jconf)
      self.prefix   =           self.jconf['prefix'] #префикс точек списка подписки
      self.retprefix   =        self.jconf['retprefix'] #префикс точек ответа подписки в ответе str(node.nodeid.Identifier)
      self.connectionstatus =   str()#первые символы префикса "ns=4;s=" там отсуствуют
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
        self.Value[self.retprefix+p["address"]] = ""
        #print (self.SubscribeNodes)
#--------------------------------------------------------
    def getValueShort(self,short)->str: 
        #возращает значение сохраненое в основном цикле
        return str(self.Value[str(self.retprefix)+short])
#--------------------------------------------------------
    async def getNodeShort(self,short)->Node:
        #возвращает обьект Node по адресу
        return self.client.get_node(self.prefix+self.retprefix+short)
#--------------------------------------------------------
    async def WriteValueShort(self,short,val):
        #производит запись значения в точку, предварительно определив ее тип для корректного преобразования типа
        #нужно добавить ловушки для ошибок, с этим в докуменации туго
            if self.connectionstatus == 'Connected':
              writenode= self.client.get_node(self.prefix+self.retprefix+short)
              t=await writenode.read_data_type_as_variant_type()
              if type(t)==ua.VariantType:
                dv = ua.DataValue(ua.Variant(val,t))
                await writenode.write_value(dv)
            
            #работающий пример
              #struct = client.get_node("ns=4; s=|var|WAGO 750-8212 PFC200 G2 2ETH RS.Application.GVL.AIArray.AI[2].AIData.MaxRaw")
            # dv = ua.DataValue(ua.Variant(33, ua.VariantType.UInt16))
              #s=await struct.read_data_type_as_variant_type()
              #await struct.write_value(dv) р
  #--------------------------------------------------------           

      
    def  __str__(self)->str:
        #возвращает имя и url фермы
        return f"{self.name} {self.URL}"
    
    def PrintValues(self,fields:list=[]):
        #передаем список точек для печати или напечатаем все по умолчанию
        self.t=PrettyTable(["Point name","Value"])
        for x in self.pointsdata["Tag"]:
                self.t.add_row([x["address"], self.getValueShort(x["address"])])
        print(self.jconf["name"],self.connectionstatus)
        print(self.t) 
    



    
    async def loop(self):
        #метод для зацикливания ,
        while True:
            self.handler = SubHandler() #указатель на класс обработки подписки
            self.client   =   Client(url=self.URL)  #клиент  фермы
            self.client.set_user(self.jconf["login"])
            self.client.set_password(self.jconf["password"])
            try: #ловушка от дисконектов
                async with self.client: 
                    self.subscription = await self.client.create_subscription(1500, self.handler) # создаем подписку с указателем на класс с методом и таймаутом 1500
                    self.nodes_to_read = [Node(self.client, n) for n in self.SubscribeNodes]
                   # print(self.nodes_to_read)
                    
                    await self.subscription.subscribe_data_change(nodes=self.nodes_to_read, 
                    attr=ua.AttributeIds.Value, 
                    queuesize=50, )
         
                    while True: #цикл опроса изменения подписки 
                        await asyncio.sleep(1)
                        if self.handler.datachanged:
                            self.Value=self.handler.Value.copy()  # передаем копию считаных данных в массив значений
                            self.handler.datachanged=False
                            self.connectionstatus='Connected'
                            #!!эта строка ниже нужна для отображения передачи с клиентов для проверки если не работает метод запроса
                            #for n in self.value: print(n,self.value[n], '\n ' ) 
                        await self.client.check_connection()  # отсюда вызывается исклюение об обрыве связи и запускается реконнект клиента 
            except (ConnectionError, ua.UaError,asyncio.exceptions.TimeoutError):
               #_logger.warning("Reconnecting in 2 seconds")
                self.connectionstatus='Timeout!'
                await asyncio.sleep(2)
     
               
    

          

                

    


"""
if __name__ == "__main__":

    logging.basicConfig(level=logging.INFO)
    asyncio.run(main())
    """
