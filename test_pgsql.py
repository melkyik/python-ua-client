
import psycopg2
from psycopg2 import Error
import json
import asyncio
import logging
from FarmClass import FarmPLC,FarmList

mylogger = logging.getLogger("ifarm")
farms=FarmList("Список ферм из базы")
"""Список ферм класc FarmList"""
class ifarmPgSql: 
    """класс определяет подключение к субд PostgreSql"""
    def __init__(self) -> None:
        pass
    def connect(self):
        try:
            # Подключение к существующей базе данных
            self.connection = psycopg2.connect(user="igor",
                                        # пароль, который указали при установке PostgreSQL
                                        password="adminsa",
                                        host="10.10.2.152",
                                        port="5432",
                                        database="ifarm")

            # Курсор для выполнения операций с базой данных
            with self.connection.cursor() as cursor:
                # Распечатать сведения о PostgreSQL
                mylogger.info("Информация о сервере PostgreSQL")
                mylogger.info(f"{self.connection.get_dsn_parameters()}\n")
                # Выполнение SQL-запроса
                cursor.execute("SELECT version();")
                # Получить результат
                record = cursor.fetchone()
                mylogger.info(f"Вы подключены к - {record,} \n")

        except (Exception, Error) as error:
            mylogger.warning("Ошибка при работе с PostgreSQL >%s", error)
#--------------------------------------------------------
    def close(self):   
            """разрыв соединения"""  
            if self.connection:
                self.connection.close()
                mylogger.info("Соединение с PostgreSQL закрыто")
#--------------------------------------------------------                
    def get_farm_settings(self)->list:
        """считывание параметров связи для фермы""" 
        if self.connection:
            with self.connection.cursor() as cursor:
                query= "SELECT scada_settings.title\
                ,scada_settings.settings\
                FROM scada inner join scada_settings on scada.setting_id = scada_settings.id\
                where status='active'"
                cursor.execute(query)
                return cursor.fetchall()
#--------------------------------------------------------    
    def getpointsforfarm(self,farm)->list:
        """считывание списка точек, где 1 позиция  - имя точки, вторая позиция описание"""
        if self.connection:
            with self.connection.cursor() as cursor:
                query= f"SELECT identity,scada_sensors.title title\
                        FROM public.scada_sensors \
                        inner join scada on scada_id=scada.id \
                        inner join scada_settings on setting_id=scada_settings.id\
                        WHERE scada_sensors.status='active'\
                        and scada_settings.title = '{farm}'\
                        ;"
                cursor.execute(query)
                return cursor.fetchall()

        

def extract_point_name(s)->list:
    """считывает имя точки и парсит его на составляющие - префиксы и имя"""
    if s.find('RS.Application.'):
        return s[s.find('RS.Application.')+15:],s[s.find("|var|"):s.find('RS.Application.')+15],"ns=4;s="
    else:
        return [s,'','']




async def main():
        tasks=[]
        for k in farms.farms:
                tasks.append(asyncio.create_task(farms.get(k).loop()))
        tasks.append(asyncio.create_task(printfarms()))
        await asyncio.gather(*tasks)

async def printfarms(): 
        """процедурка для вывода считаных значений и записи переменных"""
        while True:
            print("\033c", end='') 
            for k in farms.farms:
              farms.get(k).PrintValues()
           # await fr(1).WriteValueShort("GVL.AIArray.AI[0].AIData.Value",c)  
            await asyncio.sleep(1)            

if __name__ == "__main__":

    logging.basicConfig(level=logging.WARNING,
                        format="%(asctime)s: %(message)s",
                        datefmt=  '%Y-%m-%d %H:%M:%S')
 
    base=ifarmPgSql() #
    base.connect() #зацеп к базе
    settings=base.get_farm_settings() #читаем фермы с базы
    i=0
    for k in settings:     #создание экземпляров обьектов ферм по списку
        i+=1               
        js=json.loads(k[1])
        try:
            points=base.getpointsforfarm(k[0]) #считаем список точек для этой фермы
    
            farms.add(   #вызов конструктора
            jconf={ "id":str(i),
                "name":k[0],
                "URL":f"opc.tcp://{js['opcEndpoint']['host']}:4840",
                "login":f"{js['opcEndpoint']['security']['userName']}",
                "password":f"{js['opcEndpoint']['security']['password']}",
                "prefix":"ns=4;s=",
                "retprefix":f"{extract_point_name(points[0][0])[1]}" #с 1 точки заберем префиксы для этого точки читаются выше
            }
            )
            for p in points:
                shortpoint=extract_point_name(p[0])[0],p[1]
                farms.get(i).addpoint(shortpoint)            #добавление точек в подписку и конфигурацию
         

        except KeyError as error: #ловушка на некорректную конфу в базе
            mylogger.warning(f"косяк в конфе фермы  {k[0]}, глюк в поле {error}" )
       # else:
           #for v in farms[k[0]].Value: #вывод точек и их значения
            #    mylogger.info( farms[k[0]].Value[v])
              
    base.close()

    asyncio.run(main())   
   
  
        
    
    