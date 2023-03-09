import json
from asyncua import Client, ua, Node
from asyncua.common.subscription import DataChangeNotif
from asyncua.ua.uatypes import DataValue
import logging
from logging.handlers import RotatingFileHandler
import asyncio #https://github.com/FreeOpcUa/opcua-asyncio
from prettytable import PrettyTable
from datetime import datetime
from typing import Optional



mylogger = logging.getLogger(__name__)
external_logger = logging.getLogger('asyncua')
external_logger.setLevel(logging.ERROR)

# # Create a file handler for the main module logger
# file_handler = RotatingFileHandler("main.log", maxBytes=2000, backupCount=10)
# file_handler.setLevel(logging.INFO)

# # Create a formatter for the main module file handler
# formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
# file_handler.setFormatter(formatter)
# # Add the file handler to the main module logger
# mylogger.addHandler(file_handler)

class SubHandler:
  
    def __init__(self):
        self.Value:dict[str,DataChangeNotif]           =  {} #сопоставление адреса и данных подписки
        self.datachanged     = False
    """DataChangeNotification(<asyncua.common.subscription.SubscriptionItemData object at 0x000001D010B04F10>, 
        MonitoredItemNotification(ClientHandle=201, Value=DataValue(Value=Variant(Value=19.709999084472656, VariantType=<VariantType.Float: 10>, Dimensions=None, is_array=False), StatusCode_=StatusCode(value=0), SourceTimestamp=datetime.datetime(2023, 2, 8, 13, 58, 12, 245000), ServerTimestamp=datetime.datetime(2023, 2, 8, 13, 58, 12, 245000), SourcePicoseconds=None, ServerPicoseconds=None)))
    """
    def datachange_notification(self, node: Node, val, data:DataChangeNotif):
         # called for every datachange notification from server
        # например |var|WAGO 750-8212 PFC200 G2 2ETH RS.Application.PLC_PRG.counter
        #self.Value[str(node.nodeid.Identifier)]=data# обращаемся к точке по retadr не эффективно - будем искать точки по  полному адресу как ниже!
        self.Value[str(data.subscription_data.node)]=data 
       
        self.datachanged=True
        #print(val)
        
    def event_notification(self, event: ua.EventNotificationList):
       #called for every event notification from server
        pass
    def status_change_notification(self, status: ua.StatusChangeNotification):
        #called for every status change notification from server
       # mylogger.info("status_notification %s", status)
        pass

    def get(self,s:str)-> DataChangeNotif:
        """возвращает данные точки подписки по ее id"""
        return(self.Value.get(s))



    
class PointTag: 
# Python 3.10+
#def get_cars(size: str|None=None):
    #в планах перевести точки в этот класс где будут хранится нужные параметры в том числе статус записи
    def __init__(self,addr:str,name:Optional[str]=None,baseid:Optional[str]=None,archive:Optional[bool]=False):
        self.baseId=baseid
        """ ссылка на ID таблицы PostgreSQL """
        self.addr=addr
        """ адрес точки"""
        self.uatype=None
        """ OPC тип точки ua.VariantType"""
        self.oldval=None
        """ предыдущее значение """
        self.value=None
        """ текущее значение """
        self.status=False
        """ статус точки """
        self.name=name
        """ имя точки """
        self.plcdate=None
        """ время обновления точки """
        self.archve=archive
        """ архивация точки """
        self.node:Node=None
        """ссылка на экземпляр Node """
        self.readed_node_full_name:str=None
        """прочитанное полное имя точки из подписки """

         
 
    def __str__(self) -> str:
        return f"{str(self.name) if self.name else str(self.addr)} {str(self.value)}"

    def get_dict(self)->dict:
        return {"id":self.baseId,
                "addr":self.addr,
                "fulladdr":str(self.node),
                "name":str(self.name),
                "plcdate":str(self.plcdate),
                "archive":self.archve,
                "value":self.value,
                "status":self.status}

            

    def get_list(self)->list:
        return self.name if self.name else self.addr, self.value       
               
    def get_sql_string(self)->str:
        if self.archve and self.status :
            return f"INSERT INTO public.scada_data2(\
sensor_id, value, timestamp, checked) \
VALUES ({self.baseId}, {self.value}, '{datetime.now()}', false);"
        else:
             return ''
#--------------------------------------------------------
# класс экземпляров клиентов ферм
#--------------------------------------------------------
class FarmPLC:
    """
    Класс обработки плк ферм. При инициализации передать словарь в виде
      jconf:dict={ "id":"1",
      "name":"PLC default",
      "URL":"opc.tcp://10.10.2.244:4840",
      "login":"admin",
      "password":"wago",
      "prefix":"ns=4;s=",
      "retprefix":"|var|WAGO 750-8212 PFC200 G2 2ETH RS.Application."
      },
    """
    def __init__(self,jconf:dict={ "id":"1",
      "name":"PLC default",
      "URL":"opc.tcp://10.10.2.244:4840",
      "login":"admin",
      "password":"wago",
      "prefix":"ns=4;s=",
      "retprefix":"|var|WAGO 750-8212 PFC200 G2 2ETH RS.Application."
      },log=False):
      self.close=False
      #инициализация и заполнение первичными данными из конфигурационного файла
      self.Value               =  {} #сопоставление короткого адреса и текущего значения, словарь текущих значений 
      self.jconf    =           jconf.copy()
      #print(self.jconf)
      self.prefix   =           str(self.jconf['prefix']) #префикс точек списка подписки
      self.retprefix   =        str(self.jconf['retprefix']) #префикс точек ответа подписки в ответе str(node.nodeid.Identifier)
                                                #первые символы префикса "ns=4;s=" там отсуствуют
      self.connectionstatus =   str()
      self.name     =           str(self.jconf['name'] )
      self.URL      =           str(self.jconf['URL'])
      self.SubscribeNodes    =  list() #список точек для подписки, остальные опрашиваются по общему опросу
      self._maxbrowselevel=1
 
    def addpoint(self,addresses:list):
        """
        Добавляет точку по формату из начала списка 
        addresses[0]= имя точки, 
        addresses[1]= описание точки
        addresses[2]= id в базе
        addresses[3] = true - архивировать точку в тренд
        """
        s=self.prefix+self.retprefix+addresses[0]
        self.SubscribeNodes.append(s)
        self.Value[addresses[0]] = PointTag(
                addr=addresses[0], 
                name=addresses[1],
                baseid=addresses[2],
                archive=addresses[3]
                 )
    def loadpointsfromfile(self,filename):
      """
      загружаем стандартные точки из файла
      """
      with open(filename, "r") as read_file: 
        self.pointsdata = json.load(read_file)
        for p in self.pointsdata['Tag']:
            s=self.prefix+self.retprefix+p["address"]
            self.SubscribeNodes.append(s)
            self.Value[p["address"]] = PointTag(
                addr=p["address"], 
                name=p["name"],
                 )
#--------------------------------------------------------
    def getTagByShort(self,s:str)->PointTag:
        """транслятор указателя на точку в коротком адресе в тип PointTag для удобства"""
        try:
        #транслятор указателя в тип PointTag для удобства кода и спелчека 
            if isinstance(self.Value[s],PointTag):
                return self.Value[s]
        except(KeyError):
                return None
#--------------------------------------------------------
    def getValueShort(self,short)->str: 
        """ возращает значение сохраненое в основном цикле"""      
        res=self.getTagByShort(short).value
        try:
            if res in (True,False):
                return str(res)
            s=float(res)
            return f"{s:.2f}"
        except :
            return str(res)
         
#--------------------------------------------------------
    def getTagByBaseId(self,baseid)->PointTag: 
        """
        возращает тэг по имени в базе
        """
        for i in self.Value:
            if self.getTagByShort(i).baseId==baseid:
                return self.getTagByShort(i)
        return None

#--------------------------------------------------------
    def getPointByRetAddr(self,retaddr)->PointTag:
            """ возвращает точку по ее RetAdr""" 
               
            for i in self.Value:
                if (self.retprefix+i)==retaddr:
                    return self.Value[i]
            return None
    def getPointByFullAddr(self,fulladr)->PointTag:
            """возвращает точку по ее полному адресу"""  
            for i in self.Value:
                if (self.prefix+self.retprefix+i)==fulladr:
                    return self.Value[i]
            return None
#--------------------------------------------------------
    def getNodeShort(self,short)->Node:
        """
        возвращает обьект Node по короткому адресу читая из сервера 
        """
        
        #if self.getTagByShort(short).node:
        #    return self.getTagByShort(short).node
       # else:
        self.getTagByShort(short).node =self.client.get_node(self.prefix+self.retprefix+short)
        return self.getTagByShort(short).node 

    def _getNodeShort_TA(self,short)->Node:
        """
        возвращает обьект Node по короткому адресу читая из списка точек, обновленных подпиской 
        """
        return self.getTagByShort(short).node
#--------------------------------------------------------           
    async def WriteValueShort(self,short,val)->bool:
        """
        производит запись значения по адресу, предварительно определив ее тип для корректного преобразования типа
        """
        if self.connectionstatus == 'Connected':
            tag=self.getTagByShort(short)
            if not tag:                         #бывает надо записать точку которой нет в подписке пока пусть будет это условие. оно создаст новую точку в словаре
                self.Value[short]=PointTag(short,short) # позже лучше это удалить
                tag=self.Value[short]

            try:

                await self.client.check_connection()
                writenode=  self.getNodeShort(short)
                #mylogger.warning("запись %s тип %s значение %s",writenode, str(tag.uatype),val)
                #if not (type(tag.uatype)==ua.VariantType): #тип точки лучше сохранить тк он точно не будет менятся
                tag.uatype=await writenode.read_data_type_as_variant_type() #произведем чтение типа данных с OPC
                if (type(tag.uatype)==ua.VariantType): #если уже записан тип в переменную - читать не обязательно
                    mylogger.warning("запись %s тип %s значение %s",short, str(tag.uatype),val)
                    if tag.uatype==ua.VariantType.Float:
                        dv = ua.DataValue(ua.Variant(float(val),tag.uatype)) #формируем значение особого типа для передачи на opc
                    elif  tag.uatype in [ua.VariantType.Int16,ua.VariantType.Int32,ua.VariantType.Int64,ua.VariantType.UInt16,ua.VariantType.UInt32,   ua.VariantType.UInt64 ]:
                        dv = ua.DataValue(ua.Variant(int(val),tag.uatype)) #формируем значение особого типа для передачи на opc
                    elif tag.uatype ==ua.VariantType.Boolean:
                         dv = ua.DataValue(ua.Variant(bool(val),tag.uatype))
                    elif tag.uatype ==ua.VariantType.String:
                        dv = ua.DataValue(ua.Variant(str(val),tag.uatype))
                    else :
                        mylogger.warning("ошибка неизвестный тип %s! %s",tag.uatype,short)
                    await writenode.write_value(dv)#произведем запись
            except (Exception, ua.UaError) as error:
                mylogger.warning("ошибка записи %s! %s",short,error)
                return False
            else:
                mylogger.debug(f"значение записано {self.getTagByShort(short).addr} {self.getTagByShort(short).oldval} -> {val}")
                await self.updatevalue(short)
                return True


    async def updatevalue(self,short)->str:
        """для обновления значения по адресу без учета подписки
        """
        try:
            await self.client.check_connection()
            node=  self.getNodeShort(short=short)
            param=await node.read_data_value()
            """ пример
            DataValue(Value=Variant(Value=21.84000015258789, VariantType=<VariantType.Float: 10>, 
                                    Dimensions=None, is_array=False), 
                     StatusCode_=StatusCode(value=0), 
                     SourceTimestamp=datetime.datetime(2023, 2, 8, 11, 12, 53, 725000), 
                     ServerTimestamp=None, SourcePicoseconds=None, ServerPicoseconds=None)
            """
            if not self.getTagByShort(short):                         #бывает надо обратится к точке которой нет в подписке пока пусть будет это условие. оно создаст новую точку в словаре
               self.Value[short]=PointTag(short,short)                # позже лучше это удалить
            if not self.getTagByShort(short).uatype: 
                self.getTagByShort(short).uatype= param.Value.VariantType
            self.getTagByShort(short).value=param.Value.Value
            self.getTagByShort(short).plcdate=param.SourceTimestamp
            return self.getTagByShort(short).value

        except:
            mylogger.warning("Ошибка чтения %s",short)
            return None
        finally:
            if (self.getTagByShort(short).value != self.getTagByShort(short).oldval) :
                self.getTagByShort(short).oldval=self.getTagByShort(short).value
      
    def  __str__(self)->str:
        """возвращает имя и url фермы
        """
        return f"{self.name} {self.URL}"
    
    def PrintValues(self,fields:list=[]):
        """передаем список точек для печати или напечатаем все по умолчанию"""
        t=PrettyTable(["Point name","Value"])
        for x in self.Value:
             t.add_row([self.getTagByShort(x).name,self.getValueShort(x)])#)
        print(self.jconf["name"], self.connectionstatus)
        print(t) 
    



    #--------------------------------------------------------  
    async def loop(self):
     """метод для зацикливания опроса, """
     try:
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
                            for i in self.handler.Value:
                                buf=self.getPointByFullAddr(i)
                                if buf:
                                    buf.oldval   =   buf.value
                                    buf.value    =   self.handler.get(i).monitored_item.Value.Value.Value
                                    buf.node     =   Node(self.handler.get(i).subscription_data.client_handle, self.handler.get(i).subscription_data.node)
                                    buf.plcdate  =   self.handler.get(i).monitored_item.Value.SourceTimestamp
                                    buf.uatype   =   self.handler.get(i).monitored_item.Value.data_type
                                    buf.status   =   self.handler.get(i).monitored_item.Value.StatusCode.is_good()
                                    buf.readed_node_full_name=str(self.handler.get(i).subscription_data.node)
                                  # передаем копию считаных данных в массив значений
                            self.handler.datachanged=False
                            self.handler.Value={}
                            self.connectionstatus='Connected'
                            #!!эта строка ниже нужна для отображения передачи с клиентов для проверки если не работает метод запроса
                            #for n in self.value: print(n,self.value[n], '\n ' ) 
                        await self.client.check_connection()  # отсюда вызывается исклюение об обрыве связи и запускается реконнект клиента 
            except (ConnectionError, ua.UaError,asyncio.exceptions.TimeoutError,OSError) as error:
                mylogger.warning("%s-%s Reconnecting in 30 seconds",self.name,error)
                self.connectionstatus='Timeout!'
                await asyncio.sleep(30)
     except(asyncio.exceptions.CancelledError)as  error:
        mylogger.info("%s-%s exit cycle ",self.name,error)

    async def browse_nodes(self, node: Node,level:int=0,maxbrowselevel:int=0):
        """
        возвращает тип ноды и ее дочерние ноды. level - уровень поиска рекурсии, maxbrowselevel макс уровень вложености
        """
        node_class = await node.read_node_class()
        children = []
        child:Node
        strchildren:list[str]=[]
        for child in await node.get_children():
            if await child.read_node_class() in [ua.NodeClass.Object, ua.NodeClass.Variable]:
                if level < maxbrowselevel:
                    children.append(await self.browse_nodes(child,level=level+1,maxbrowselevel=maxbrowselevel))
                else:
                    children.append(child)  

                strchildren.append(str(child))
        if node_class != ua.NodeClass.Variable:
            var_type = None
        else:
            try:
                var_type = (await node.read_data_type_as_variant_type()).value
            except ua.UaError:
                mylogger.warning('Node Variable Type could not be determined for %r', node)
                var_type = None
        return {
            'id': str(node),
            'name': (await node.read_display_name()).Text,
            'cls': node_class.value,
            'strchildren':strchildren,
            'children':children,
            'type': var_type,
        }
 ##
 #класс со списком ферм для удобства поиска и обращения в списке
 # 
 # 
 #                
class  FarmList:
    """класс со списком ферм для удобства поиска и обращения в списке"""
    def __init__(self,desc:str) -> None:
        self.farms:dict[str,FarmPLC]={}
        self.desc=str(desc)

    def __str__(self) -> str:
        return self.desc + str(len(self.farms))
    def get(self,id)-> FarmPLC:
        """возвращает ферму по ее id"""
        return self.farms.get(str(id))
       
          
    def add(self,jconf:dict={ "id":"1",
      "name":"PLC default",
      "URL":"opc.tcp://10.10.2.244:4840",
      "login":"admin",
      "password":"wago",
      "prefix":"ns=4;s=",
      "retprefix":"|var|WAGO 750-8212 PFC200 G2 2ETH RS.Application."
      }):
      """добавляет ферму в список на ввводе нужно указать
      jconf:dict={ "id":"1",
      "name":"PLC default",
      "URL":"opc.tcp://10.10.2.244:4840",
      "login":"admin",
      "password":"wago",
      "prefix":"ns=4;s=",
      "retprefix":"|var|WAGO 750-8212 PFC200 G2 2ETH RS.Application." """
      self.farms[jconf["id"]] = FarmPLC(jconf)


    def get_by_name(self,name:str)->FarmPLC:
        """производит поиск и возвращает экземпляр FarmPLC по имени name """
        try:
            for k in self.farms:
                if self.get(k).name == name:
                    return self.get(k)
            mylogger.warning("%s Farm isnt found! in list %s",name,self.desc)
        except (KeyError) as error:
                mylogger.warning("get_by_name keyerror!  in list %s - %s",self.desc,error)
                return None    

                
    def generate_trends(self)->str:
        buf=''
        for k in self.farms:
            for i in self.get(k).Value:
                buf+=self.get(k).getTagByShort(i).get_sql_string()
        return buf







 