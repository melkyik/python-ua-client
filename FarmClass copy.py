#бэкап от файла с реализацией подписок на абсолютно все точки фермы
import json
from icecream import ic
from asyncua import Client, ua, Node
from asyncua.common.subscription import DataChangeNotif
from asyncua.ua.uatypes import DataValue
import logging
from logging.handlers import RotatingFileHandler
import asyncio #https://github.com/FreeOpcUa/opcua-asyncio
from prettytable import PrettyTable
from datetime import datetime
from typing import Optional,List,Dict,Any
import copy
from mixtableclass import MixData
import sqlalchemy
from sqlalchemy import URL,create_engine
from sqlalchemy.orm import sessionmaker
from dotenv import load_dotenv
import os
from os.path import join, dirname
dotenv_path = join(dirname(__file__), '.env')
load_dotenv(dotenv_path)

def extract_point_name(s:str)->list:
    """считывает имя точки и парсит его на составляющие - префиксы и имя"""
    try:

        if s.find('RS.Application.'):
            return s[s.find('RS.Application.')+15:],s[s.find("|var|"):s.find('RS.Application.')+15],"ns=4;s="
        else:
            return [s,'','']
    except:
        return [s,'','']

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
        self.plcdate:datetime=None
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
    bd_URL:URL=None
    "коннект к бд mysql"
    bd_logfilter:str=None
    "фильтр таблицы message_log"
    zonenames={}
    "сопоставление имен зон"

    
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
      self.Value:dict[str,PointTag]             =  {} #сопоставление короткого адреса и текущего значения, словарь текущих значений 
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
        if self.getTagByShort(short):
            res=self.getTagByShort(short).value
            try:
                if res in (True,False):
                    return str(res)
                s=float(res)
                return f"{s:.2f}"
            except :
                return str(res)
        return "None"
         
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
    def getPointByName(self,name)->PointTag:
            """возвращает точку по ее имени """  
            for i in self.Value:
                if self.getTagByShort(i).name==name:
                    return self.getTagByShort(i)
            return None
    def getValueByName(self,name)->Any: 
        """ возращает значение сохраненое в основном цикле"""      
        if self.getPointByName(name):
            return self.getPointByName(name).value
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

    async def forcereadvalueshort(self,short):
        """для чтения значения по адресу без учета подписки. работает медленнее чем подписка
        """
        if not self.getTagByShort(short):
            try:
                await self.client.check_connection()
                node=  self.getNodeShort(short=short)
                param=await node.read_data_value()
                if not param:
                    return None
                else :                    #бывает надо обратится к точке которой нет в подписке пока пусть будет это условие. оно создаст новую точку в словаре
                    #pt=PointTag(short,short)                # позже лучше это удалить
                    #if not pt.uatype: 
                    #    pt.uatype= param.Value.VariantType
                    #pt.value=param.Value.Value
                    #pt.plcdate=param.SourceTimestamp
                    return param.Value.Value

            except:
                mylogger.warning("Ошибка чтения %s",short)
                return None
        else:
            return self.getTagByShort(short).value
  


    def  __str__(self)->str:
        """возвращает имя и url фермы
        """
        return f"{self.name} {self.URL}"
    
    def PrintValues(self,points:list):
        """передаем список точек для печати или напечатаем все по умолчанию"""
        t=PrettyTable(["Point name","Value"])
        for x in self.Value:
             if (x in points) or (points is None): 
                t.add_row([self.getTagByShort(x).name,self.getValueShort(x)])#)
        print(self.jconf["name"], self.connectionstatus)
        print(t) 
    



    #--------------------------------------------------------  
    async def loop(self):
     """метод для зацикливания опроса подписки """
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
                        await asyncio.sleep(0.5)
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
   
   #--------------------------------------------------------  
    async def mix_loop(self):
        """цикл мониторинга замесов на ферме и выдачи лога состояния этих замесов"""
        def to_int(x)->int:
            return 0 if (x is None) or (x=="None") else int(float(x))
        def to_float(x)->float:
            return 0 if (x is None) or (x=="None") else float(x)
        oldautostage=0
        oldfluidstage=0
        ecwater=0
        EC_Measured=0
        ph_Measured=0
        tanklevel=0
        start_date:datetime=None
        EC_tank=0
        fluidflag=False
        url_object = URL.create(
                    "mysql+pymysql",
                    username=os.environ.get("MIXDB_USER"),
                    password=os.environ.get("MIXDB_PASSWORD"),  # plain (unescaped) text
                    host=os.environ.get("MIXDB_HOST"),
                    database=os.environ.get("MIXDB_BASE"),
                )
        while True:
            
            auto,autostat= to_int(self.getValueShort("GVL.Command.AutoStage")),self.getTagByShort("GVL.Command.AutoStage").status,
            recipe= to_int(self.getValueShort("GVL.Command.Automate.Recipe"))
            autostage,plcdate= to_int(self.getValueShort("GVL.Command.Automate.Stage")),self.getTagByShort("GVL.Command.Automate.Stage").plcdate
            k_correct=to_float(self.getValueShort("GVL.Command.Fluid.K_correct"))
            fluidstage=to_int(self.getValueShort("GVL.Command.Fluid.Stage"))
            fluidcnt=to_int(self.getValueShort("GVL.Command.Fluid.cnt"))
            
    

            if oldautostage!=autostage:
                mylogger.info(f"{self.name} autostage ={autostage} old={oldautostage} ")
            
            if (auto==1) and autostat: #автоматический режим активен
                if ((fluidstage in [5,6,7]) and (oldfluidstage in [2,3,4])) and (fluidcnt>0) and not fluidflag:#or( datetime.now().minute==23):
                    ecwater=to_float(self.getValueShort("GVL.Command.Fluid.ECWater"))
                    tanklevel=to_float(self.getValueShort("GVL.Command.Fluid.Level"))
                    EC_tank = to_float(self.getPointByName(f'ECtank.{recipe}').value if self.getPointByName(f'ECtank.{recipe}') else None)
                    mylogger.info(f"{self.name} - ECwater = {ecwater}, tanklevel={tanklevel} ectank={EC_tank} k_correct={k_correct}")
                    fluidflag=True
                if (oldautostage !=autostage ) and (autostage in range(3,5)): #начат замес
                    mylogger.info(f"{self.name} - зафиксирован старт замеса в {plcdate} в зону {recipe}")
                    start_date=plcdate

                if (oldautostage in range(5,9)) and (autostage==9) :#or( datetime.now().minute==54 and datetime.now().second==0) :  #значит начат залив в зону
                    mylogger.info(f"{self.name} - зафиксирован залив в зону {recipe} в {plcdate}")
                    EC_Measured=to_float(self.getValueShort("GVL.Command.Fluid.EC_Measured"))
                    ph_Measured=to_float(self.getValueShort("GVL.Command.Fluid.ph_Measured"))
                 

                    try:
                        if self.getTagByShort("GVL.Command.AutoStage").status and (recipe >0):
                            engine= create_engine(url_object,echo=False)
                            Session=sessionmaker(bind=engine)
                            session=Session()
                            if (start_date=="None") or (start_date is None) :
                                raise Exception("{self.name} start_date not present")
                            row=MixData(        farm=self.name,
                                                start_mix=start_date,
                                                end_mix=plcdate,
                                                result=None,
                                                zone=recipe,
                                                zonename=self.zonenames.get(str(recipe)),
                                                rd_Automate         =self.getValueByName(f"recipedata[{recipe}].Automate"),
                                                rd_AutomateCorr     =self.getValueByName(f"recipedata[{recipe}].AutomateCorr"),
                                                rd_Cycle            =self.getValueByName(f"recipedata[{recipe}].Cycle"),
                                                rd_nCycle           =self.getValueByName(f"recipedata[{recipe}].nCycle"),
                                                rd_K                =self.getValueByName(f"recipedata[{recipe}].K"),
                                                rd_KEC              =self.getValueByName(f"recipedata[{recipe}].KEC"),
                                                rd_KpH              =self.getValueByName(f"recipedata[{recipe}].KpH"),
                                                rd_V_irrigation     =self.getValueByName(f"recipedata[{recipe}].V_irrigation"),
                                                md_Volume           = None if (tanklevel=="None") or (tanklevel is None) else tanklevel,
                                                md_ECWater          = None if (ecwater=="None") or (ecwater is None) else ecwater,
                                                md_ECTank           =None if (EC_tank=="None") or (EC_tank is None) else EC_tank,
                                                md_K_correct           = None if (k_correct=="None") or (k_correct is None) else k_correct,
                                                rd_DoseZone_0       =self.getValueByName(f"recipedata[{recipe}].DoseZone[0]"),
                                                rd_DoseZone_1       =self.getValueByName(f"recipedata[{recipe}].DoseZone[1]"),
                                                rd_DoseZone_2       =self.getValueByName(f"recipedata[{recipe}].DoseZone[2]"),
                                                rd_DoseZone_3       =self.getValueByName(f"recipedata[{recipe}].DoseZone[3]"),
                                                rd_DoseZone_4       =self.getValueByName(f"recipedata[{recipe}].DoseZone[4]"),
                                                rd_DoseZone_5       =self.getValueByName(f"recipedata[{recipe}].DoseZone[5]"),
                                                rd_DoseZone_6       =self.getValueByName(f"recipedata[{recipe}].DoseZone[6]"),
                                                rd_DoseZone_7       =self.getValueByName(f"recipedata[{recipe}].DoseZone[7]"),
                                                rd_DoseZone_8       =self.getValueByName(f"recipedata[{recipe}].DoseZone[8]"),
                                                rd_DoseZone_9       =self.getValueByName(f"recipedata[{recipe}].DoseZone[9]"),

                                                rd_EC_After_0       =self.getValueByName(f"recipedata[{recipe}].EC_After[0]"),
                                                rd_EC_After_1       =self.getValueByName(f"recipedata[{recipe}].EC_After[1]"),
                                                rd_EC_After_2       =self.getValueByName(f"recipedata[{recipe}].EC_After[2]"),
                                                rd_EC_After_3       =self.getValueByName(f"recipedata[{recipe}].EC_After[3]"),
                                                rd_EC_After_4       =self.getValueByName(f"recipedata[{recipe}].EC_After[4]"),
                                                rd_EC_After_5       =self.getValueByName(f"recipedata[{recipe}].EC_After[5]"),
                                                rd_EC_After_6       =self.getValueByName(f"recipedata[{recipe}].EC_After[6]"),
                                                rd_EC_After_7       =self.getValueByName(f"recipedata[{recipe}].EC_After[7]"),
                                                rd_EC_After_8       =self.getValueByName(f"recipedata[{recipe}].EC_After[8]"),
                                                rd_EC_After_9       =self.getValueByName(f"recipedata[{recipe}].EC_After[9]"),
                                                rd_ECStart          =self.getValueByName(f"recipedata[{recipe}].EC_Start_zone"),

                                                md_ECr_0            =None,
                                                md_ECr_1            =self.getValueByName(f"mixdata.ECr[1]"),
                                                md_ECr_2            =self.getValueByName(f"mixdata.ECr[2]"),
                                                md_ECr_3            =self.getValueByName(f"mixdata.ECr[3]"),
                                                md_ECr_4            =self.getValueByName(f"mixdata.ECr[4]"),
                                                md_ECr_5            =self.getValueByName(f"mixdata.ECr[5]"),
                                                md_ECr_6            =self.getValueByName(f"mixdata.ECr[6]"),
                                                md_ECr_7            =self.getValueByName(f"mixdata.ECr[7]"),
                                                md_ECr_8            =self.getValueByName(f"mixdata.ECr[8]"),
                                                md_ECr_9            =self.getValueByName(f"mixdata.ECr[9]"),
                                                md_dozevol_0        =None,
                                                md_dozevol_1        =self.getValueByName(f"mixdata.dozevol[1]"),
                                                md_dozevol_2        =self.getValueByName(f"mixdata.dozevol[2]"),
                                                md_dozevol_3        =self.getValueByName(f"mixdata.dozevol[3]"),
                                                md_dozevol_4        =self.getValueByName(f"mixdata.dozevol[4]"),
                                                md_dozevol_5        =self.getValueByName(f"mixdata.dozevol[5]"),
                                                md_dozevol_6        =self.getValueByName(f"mixdata.dozevol[6]"),
                                                md_dozevol_7        =self.getValueByName(f"mixdata.dozevol[7]"),
                                                md_dozevol_8        =self.getValueByName(f"mixdata.dozevol[8]"),
                                                md_dozevol_9        =self.getValueByName(f"mixdata.dozevol[9]"),
                                                md_Dosername_0      =None,
                                                md_Dosername_1      =self.getValueByName(f"mixdata.dosernames[1]"),
                                                md_Dosername_2      =self.getValueByName(f"mixdata.dosernames[2]"),
                                                md_Dosername_3      =self.getValueByName(f"mixdata.dosernames[3]"),
                                                md_Dosername_4      =self.getValueByName(f"mixdata.dosernames[4]"),
                                                md_Dosername_5      =self.getValueByName(f"mixdata.dosernames[5]"),
                                                md_Dosername_6      =self.getValueByName(f"mixdata.dosernames[6]"),
                                                md_Dosername_7      =self.getValueByName(f"mixdata.dosernames[7]"),
                                                md_Dosername_8      =self.getValueByName(f"mixdata.dosernames[8]"),
                                                md_Dosername_9      =self.getValueByName(f"mixdata.dosernames[9]"),
                                                md_ECmix=None if (EC_Measured=="None") or (EC_Measured is None) else EC_Measured,
                                                md_pHmix=None if (ph_Measured=="None") or (ph_Measured is None) else ph_Measured,
                                                        )
                            

                            
                            session.add(row)
                            session.commit()
                            session.close()
                            mylogger.info("{self.name} row added ")
                            fluidflag=False
                        else:
                            raise  Exception(f"{self.name} error recipe={recipe} или статус точки - неисправность")    
                    except Exception as error:
                        mylogger.error(error)
            oldautostage=autostage
            oldfluidstage=fluidstage
            await asyncio.sleep(1)

#---------------------------------------------------------------



    async def browse_nodes(self, node: Node,level:int=0,maxbrowselevel:int=0):
        "возвращает тип ноды и ее дочерние ноды. level - уровень поиска рекурсии, maxbrowselevel макс уровень вложености"
        node_class = await node.read_node_class()
        children = []
        child:Node
        strchildren:list[str]=[]
        typedict:dict[str,str]={}
        for child in await node.get_children():
            if await child.read_node_class() in [ua.NodeClass.Object, ua.NodeClass.Variable]:
                if level < maxbrowselevel:
                    children.append(await self.browse_nodes(child,level=level+1,maxbrowselevel=maxbrowselevel))
                else:
                    children.append(child)  
                    typedict[str(child)]= await child.read_node_class() 
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
            'typedict':typedict,
            'children':children,
            'type': var_type,

        }
    
    def get_filtered_list_of_shorts(self, search_string: str = "") -> list[str]:
        "возвращает короткие адреса по фильтру"
        return [self.Value[p].addr for p in self.Value if search_string in self.Value[p].name] 
    
    def get_filtered_list_of_names(self, search_string: str = "") -> list[str]:
        "возвращает имена точек по фильтру"
        return [self.Value[p].name for p in self.Value if search_string in self.Value[p].name] 
 ##
 #класс со списком ферм для удобства поиска и обращения в списке
 # 
 # 
 #                
# class  FarmList_: 
#     """класс со списком ферм для удобства поиска и обращения в списке"""
#     def __init__(self,desc:str) -> None:
#         self.farms:dict[str,FarmPLC]={}
#         self.desc=str(desc)

#     def __str__(self) -> str:
#         return self.desc + str(len(self.farms))
#     def get(self,id)-> FarmPLC:
#         """возвращает ферму по ее id"""
#         return self.farms.get(str(id))
       
          
#     def add(self,jconf:dict={ "id":"1",
#       "name":"PLC default",
#       "URL":"opc.tcp://10.10.2.244:4840",
#       "login":"admin",
#       "password":"wago",
#       "prefix":"ns=4;s=",
#       "retprefix":"|var|WAGO 750-8212 PFC200 G2 2ETH RS.Application."
#       }):
#       """добавляет ферму в список на ввводе нужно указать
#       jconf:dict={ "id":"1",
#       "name":"PLC default",
#       "URL":"opc.tcp://10.10.2.244:4840",
#       "login":"admin",
#       "password":"wago",
#       "prefix":"ns=4;s=",
#       "retprefix":"|var|WAGO 750-8212 PFC200 G2 2ETH RS.Application." """
#       self.farms[jconf["id"]] = FarmPLC(jconf)


#     def get_by_name(self,name:str)->FarmPLC:
#         """производит поиск и возвращает экземпляр FarmPLC по имени name """
#         try:
#             for k in self.farms:
#                 if self.get(k).name == name:
#                     return self.get(k)
#             mylogger.warning("%s Farm isnt found! in list %s",name,self.desc)
#         except (KeyError) as error:
#                 mylogger.warning("get_by_name keyerror!  in list %s - %s",self.desc,error)
#                 return None    

                
#     def generate_trends(self)->str:
#         buf=''
#         for k in self.farms:
#             for i in self.get(k).Value:
#                 buf+=self.get(k).getTagByShort(i).get_sql_string()
#         return buf

class FarmList(dict[str,FarmPLC]):
   #def __init__(self, *args, **kwargs):            
    #    super().__init__()  
    """переопределяет класс Dict;"""

    def get(self,id)-> FarmPLC:
        """возвращает ферму по ее id"""
        return super().get(str(id))   
    def add(self,jconf:dict={ "id":"1",
    "name":"PLC default",
    "URL":"opc.tcp://10.10.2.244:4840",
    "login":"admin",
    "password":"wago",
    "prefix":"ns=4;s=",
    "retprefix":"|var|WAGO 750-8212 PFC200 G2 2ETH RS.Application."
    }): 
          
        try:
            buf=FarmPLC(jconf)  
            mylogger.info(f"Farm readed {buf.jconf['id']} {buf.name}")
            self[jconf['id']]=buf
        except:
            mylogger.error(f" cant read json {jconf}")


    def get_by_name(self,name:str)->FarmPLC:
        """производит поиск и возвращает экземпляр FarmPLC по имени name """
        try:
            for k in self:
                if self[k].name == name:
                    return self.get(k)
            mylogger.warning("%s Farm isnt found! in list %s",name,self)
        except (KeyError) as error:
                mylogger.warning("get_by_name keyerror!  in list %s - %s",self,error)
                return None
    def generate_trends(self)->str:
        buf=''
        for k in self:
            for i in self.get(k).Value:
                buf+=self.get(k).getTagByShort(i).get_sql_string()
        return buf   


# def expand_list(j,keyword:str,rng=(0,2))->Any:
#     def has_rec_keyword(value, keyword):
#         """проверка условия что префикс есть в значении или подзначениях и с ним нужно работать"""
#         if isinstance(value, str) and keyword in value:
#             return True
#         elif isinstance(value, dict):
#             return any(has_rec_keyword(sub_value, keyword) for sub_value in value.values())
#         elif isinstance(value, list):
#             return any(has_rec_keyword(sub_value, keyword) for sub_value in value)
#         return False  
    
#     if  isinstance(j, str) and has_rec_keyword(j, keyword):
#         return [j.replace(keyword, str(i)) for i in range(rng[0], rng[1] + 1)]    
    
#     if isinstance(j, dict) and has_rec_keyword(j, keyword):
#         duplicated_dict = copy.deepcopy(j)
#         for key, value in duplicated_dict.items():
#             if isinstance(value, str) and keyword in value :
#                 duplicated_dict[key] = expand_list(value,keyword, rng)
#             elif isinstance(value, dict) and has_rec_keyword(value, keyword):
#                 duplicated_dict[key] = []
#                 for _ in range(rng[0], rng[1] + 1):
#                     new_dict = copy.deepcopy(value)
#                     for sub_key, sub_value in new_dict.items():
#                         if isinstance(sub_value, str) and keyword in sub_value:
#                             new_dict[sub_key] = sub_value.replace(keyword, str(_))
#                     duplicated_dict[key].append(new_dict)
            
#         return duplicated_dict
    
#     if  isinstance(j, list):
#         return [expand_list(value,keyword, rng) for value in j]
#     return j  
 
 
 
 
 ##
 #"словарь для удобной работы с вложеными элементами"
 # 
 # 
 #         
class BrowseDict(dict):
    "словарь для удобной работы с вложеными элементами для словаря конфигурации фермы "
    def __init__(self, input_dict):
        super().__init__(input_dict)

    def get_child(self, path:str):
        keys = path.split('.')
        current_data = self
        for key in keys:
            if '[' in key and ']' in key:
                index_start = key.index('[')
                index_end = key.index(']')
                index = int(key[index_start + 1:index_end])
                key = key[:index_start]
                if isinstance(current_data.get(key), list) and index < len(current_data.get(key)):
                    current_data = current_data[key][index]
                else:
                    return None
            elif key in current_data:
                current_data = current_data[key]
            else:
                return None
        return current_data
    
    def find_substring_path(self, substring):
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

        return search_path(self, "")
    
    def get_values(self,  find_key="", nested=True):
        "выводит список точек с ключом find key"
        values = []
        found_key = False

        def explore_dict(d, prefix=""):
            nonlocal found_key
            if isinstance(d, dict):
                for key, value in d.items():
                    current_key = f"{prefix}.{key}" if prefix else key
                    if isinstance(value, str):
                        if found_key or not find_key or (find_key and key == find_key):
                            values.append((current_key, value))
                    if nested and isinstance(value, (dict, list)):
                        explore_dict(value, current_key)
                    if key == find_key:
                        found_key = True
                        explore_dict(value, current_key)
                        return 
            elif isinstance(d, list):
                for i, item in enumerate(d):
                    explore_dict(item, f"{prefix}[{i}]" if prefix else f"[{i}]")
            elif isinstance(d, str):
                if found_key or not find_key :
                    values.append((prefix, d))
        explore_dict(self)
        return values


    
   
def extract_prefix(d)->dict:
    "преобразует префиксы конфигурации в развернутые списки внутри словаря"
    def expand_list(j,keyword:str,rng=(0,2))->Any:
        def has_rec_keyword(value, keyword):
            """проверка условия что префикс есть в значении или подзначениях и с ним нужно работать"""
            if isinstance(value, str) and keyword in value:
                return True
            elif isinstance(value, dict):
                return any(has_rec_keyword(sub_value, keyword) for sub_value in value.values())
            elif isinstance(value, list):
                return any(has_rec_keyword(sub_value, keyword) for sub_value in value)
            return False  
        
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
    "распаковываем конфигурацию из словаря с префиксами"
    fu=copy.deepcopy(d)
    fu=expand_list(fu,"%REC%",(int(fu["recipes_range"][0]), int(fu["recipes_range"][1])))
    #распаковка дозаторов в рецептах в первую очередь
    #затем распаковка в массиве словарей рецептов - префикса дозаторов, преобразование записей в списки
    
    fu["recipedata"]=[expand_list(i,"%DOSER%",(int(fu["dosers_range"][0]), int(fu["dosers_range"][1]))) for i in fu["recipedata"]]
    #распаковка дозаторов в разделе mixdata

    md=fu["mixdata"]

    fu["mixdata"]=expand_list(md,"%DOSER%",(int(fu["dosers_range"][0]), int(fu["dosers_range"][1]))) 

    return fu




 