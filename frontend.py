#вывод интерфейса для работы с базой логов
import sys
from streamlit.web import cli as stcli
import streamlit as st
from streamlit import runtime
import yaml
from yaml.loader import SafeLoader
import streamlit_authenticator as stauth
import numpy as np
#from bokeh.plotting import figure
#from bokeh.models import ColumnDataSource
#from bokeh.layouts import gridplot

import datetime 
import os
import json
import copy
import pandas as pd
from pandas import Timestamp
from icecream import ic
from sqlalchemy import URL,create_engine
from zoneinfo import ZoneInfo,available_timezones
from functools import lru_cache 

from dotenv import load_dotenv
from os.path import join, dirname
#=========================================================
#КОНФИГ ИНТЕРФЕЙСА
st.set_page_config(page_title='Информация о замесах',
                    page_icon=":bar_chart:",
                    layout="wide"
                    )

#=========================================================
if 'workdir' not in st.session_state:
    dotenv_path = join(dirname(__file__), '.env')
    load_dotenv(dotenv_path)
    st.session_state["workdir"]=os.environ.get("WORK_DIR")

#=========================================================
#авторизация немного глючит производит лишнее обновление страницы после фильтра плюс нужно ставить проверку переменной перед рендером почти всего

if 'authconfig' not in st.session_state:
    filepath=join(dirname(__file__), 'auth/auth.yaml')
    with open(filepath) as file:
        st.session_state["authconfig"] = yaml.load(file, Loader=SafeLoader)
        
authenticator = stauth.Authenticate(
        st.session_state["authconfig"]['credentials'],
        st.session_state["authconfig"]['cookie']['name'],
        st.session_state["authconfig"]['cookie']['key'],
        st.session_state["authconfig"]['cookie']['expiry_days'],
        st.session_state["authconfig"]['preauthorized']
    )    
st.session_state["name"], st.session_state["authentication_status"], st.session_state["username"] = authenticator.login(location= 'sidebar')
if st.session_state["authentication_status"]:
   authenticator.logout('Logout', 'sidebar')
elif st.session_state["authentication_status"] == False:
    st.sidebar.error('Логин/пароль неверный')
elif st.session_state["authentication_status"] == None:
    st.sidebar.warning('Введите логин и пароль')

def fl(a):
    try:
        return float(a)
    except:
        return 0
#=========================================================
#ЗАГРУЗКА ДАННЫХ ФЕРМ ИЗ КОНФ JSON
@st.cache_data
def getconfig()->dict:
    'ЗАГРУЗКА КОНФИГУРАЦИЙ С ФАЙЛА'
    settings=[]  
    files:list[str]= os.listdir(os.environ.get("WORK_DIR"))
    for file_name in files:
        file_path = os.path.join(os.environ.get("WORK_DIR"), file_name)
        if os.path.isfile(file_path) and file_name.lower().endswith('.json') and not file_name.lower().__contains__('_'):
                with open(file_path, "r") as read_file: 
                    settings.append(json.load(read_file))
    ret={}
    for k in settings:     #создание экземпляров обьектов ферм по списку 
        fucnt=0
    
       
        for fu in k["plcip"]:
            fucnt+=1
            ret[f"{k['farmname']} FU{fucnt}"]={}
            ret[f"{k['farmname']} FU{fucnt}"]['timezone']=k['timezone']
            ret[f"{k['farmname']} FU{fucnt}"]["scada"]=copy.deepcopy(k["scada"])
            ret[f"{k['farmname']} FU{fucnt}"]["ECGraph"]=copy.deepcopy(k["plcip"][fu]["ECGraph"])
            ret[f"{k['farmname']} FU{fucnt}"]["logfilter"]=copy.deepcopy(k["plcip"][fu]["logfilter"])
  
    return ret

st.session_state["farmconf"]=getconfig() 
#st.write(st.session_state["farmconf"])
#=========================================================
#РАБОТА СО ВРЕМЕНЕМ
#tzone=ZoneInfo('Asia/Novosibirsk')
if 'timezone' not in st.session_state:
    st.session_state["timezone"]='Asia/Novosibirsk'
today = datetime.datetime.now(tz=ZoneInfo('Asia/Novosibirsk'))
yesterday= today+datetime.timedelta(days=-1)


@st.cache_data
def get_timezones():
    return available_timezones()

def tzcnv(t:Timestamp):
        #cперва локализует время в utc затем пеерводит в целевой часовой пояс
        buf:Timestamp=t.tz_localize(ZoneInfo("UTC")).tz_convert(ZoneInfo(st.session_state["timezone"]))
        return buf.strftime('%Y-%m-%d %X')
def tzchange():
    global tzone
    tzone=ZoneInfo(st.session_state["timezone"])

def datetupleconvert(dat)->list:
    if type(dat)==tuple:
        if len(dat)==2:    
            ic(dat)
            dt_b = datetime.datetime(
                    year=dat[0].year,
                    month=dat[0].month,
                    day=dat[0].day,
                    hour=0,
                    minute=0,
                    second=0
                    )
            dt_e = datetime.datetime(
                    year=dat[1].year,
                    month=dat[1].month,
                    day=dat[1].day,
                    hour=23,
                    minute=59,
                    second=59
                    )
        else:
           return None
    else:
        dt_b=yesterday
        dt_e=today   
    return dt_b,dt_e

#=========================================================
#РАБОТА С ФИЛЬТРОМ
@st.cache_data
def datechange(dat:tuple)->pd.DataFrame:
    
    dc=datetupleconvert(dat)
    if dc is None:
        return None

    dt_b,dt_e=dc
    url_object = URL.create(
                "mysql+pymysql",
                username=os.environ.get("MIXDB_USER"),
                password=os.environ.get("MIXDB_PASSWORD"),  # plain (unescaped) text
                host=os.environ.get("MIXDB_HOST"),
                database=os.environ.get("MIXDB_BASE"),
            )
    engine= create_engine(url_object,echo=True)
    with engine.connect() as conn, conn.begin():  
        df = pd.read_sql_query(f"SELECT * FROM mixdata where `start_mix` BETWEEN '{dt_b}' AND '{dt_e}'", conn)  
        return df
    # ic(data)
#=========================================================
#ЗАГРУЗКА ДАННЫХ ГРАФИКА ЗОНЫ
from typing import Tuple
@st.cache_data
def getgraphdata(farmname,zone)->Tuple[pd.DataFrame,pd.DataFrame,float]:
    "ЗАГРУЗКА ГРАФИКА ЗОНЫ"
    if farmname in st.session_state['farmconf']:
        fc=st.session_state['farmconf'][farmname]
        url_object = URL.create(
        "mysql+pymysql",
        username=fc["scada"]['dbuser'],
        password=fc["scada"]['dbpass'], 
        host    =fc["scada"]['dbhost'],
        database=fc["scada"]['dbname'],
        )
    
        weekago= today+datetime.timedelta(days=-7)
        three_daysago=today+datetime.timedelta(days=-3)
        dt_b,dt_e=datetupleconvert(tuple([weekago,today]))
        dt_b3,dt_e3=datetupleconvert(tuple([three_daysago,today]))
        engine= create_engine(url_object,echo=True)
        with engine.connect() as conn, conn.begin():  
            df = pd.read_sql_query(f"SELECT `Timestamp` as ts ,`Value`as val FROM trends_hour where `id` = {fc['ECGraph'][str(zone)]} and quality=1 and `Timestamp` BETWEEN '{dt_b}' AND '{dt_e}'", conn) 
            df3days= pd.read_sql_query(f"SELECT `Timestamp` as ts ,`Value`as val FROM trends_hour where `id` = {fc['ECGraph'][str(zone)]} and quality=1 and `Timestamp` BETWEEN '{dt_b3}' AND '{dt_e3}'", conn) 
            df3days['ts'] = pd.to_numeric(df3days['ts'])
            coefficients = np.polyfit(df3days['ts'], df3days['val'], 1)
            poly = np.poly1d(coefficients)
            derivative = np.polyder(poly)
            dfp=pd.DataFrame({"ts":df['ts'],
                              "val":poly(pd.to_numeric(df['ts']))})
            angle=np.rad2deg(np.arctan(derivative(0)))
            #angle=derivative(0)
            #angle=coefficients
            dfp['ts'] = pd.to_datetime(dfp['ts'])
            return df,dfp,angle
#=========================================================
#ЗАГРУЗКА ДАННЫХ ЛОГА ЗАМЕСА
@st.cache_data
def getlogdata(farmname,dt_b,dt_e)->pd.DataFrame:
    "ЗАГРУЗКА лога"
    if farmname in st.session_state['farmconf']:
        fc=st.session_state['farmconf'][farmname]
        url_object = URL.create(
        "mysql+pymysql",
        username=fc["scada"]['dbuser'],
        password=fc["scada"]['dbpass'], 
        host    =fc["scada"]['dbhost'],
        database=fc["scada"]['dbname'],
        )

    engine= create_engine(url_object,echo=True)
    with engine.connect() as conn, conn.begin():  
        df = pd.read_sql_query(f"SELECT `Timestamp` AS TIME , TEXT AS message  from messages_data where {fc['logfilter']} AND `Timestamp`  BETWEEN '{dt_b}' AND '{dt_e}' ORDER BY TIME desc ", conn)  
        return df
def pc(a,b,com:str=""):
    "вспомогательная функция для вывода дельты в процентах"
    try:
        buf="{:.2%} ".format(1-b/a)+com
        return buf
    except:
        return None 

#def main():
#=========================================================
#НАЧАЛО РЕНДЕРА ИНТЕРФЕЙСА
if  st.session_state["authentication_status"]:
    st.sidebar.header("Фильтр")
    col=st.sidebar.columns(2)

    with col[0]:
        if col[0].button("Очистить кеш"):
            st.cache_data.clear()



    with col[1]:
        col[1].selectbox("Часовой пояс",options=available_timezones(),key="timezone")
        col[1].write('Текущий часовой пояс %s' % st.session_state["timezone"])
        



    intdates=st.sidebar.date_input(label="Выберите диапазон дат",
        value=(yesterday,today),min_value=None,max_value=None,
        format="DD.MM.YYYY",key='maindates'
    ) 
    df=datechange(intdates)  
    if not df is None:#ФИЛЬТРЫ НА САЙДБАРЕ
        farms=st.sidebar.multiselect("Фермы",
                                options=df["farm"].unique(),
                                default=df["farm"].unique()
                                ) 

        dfi=df.query("farm==@farms")
        zones=st.sidebar.multiselect("зоны",
                                options=dfi["zonename"].unique(),
                                default=dfi["zonename"].unique()
                                ) 
        dfi=df.query("farm==@farms & zonename==@zones")
###ОБРАБОТКА КНОПОК
    #нужно переделать вывод этого куска тк не работает при обновлении из за авторизации(
    def button_on_click(i):
        "ОБРАБОТКА ДИНАМИЧЕСКОЙ КНОПКИ ПОСЛЕ ФИЛЬТРАЦИИ"
        if not i in dfi['start_mix'].keys():
            return 0
        info_exp=st.expander("Информация о замесе",expanded=True)
        doser_names=["Измерение"]
        dozezone=[""]
        ecafter=[""]
        ecafter2=[]
        dosevol=[""]
        ecr=[""]
        df=pd.DataFrame()
    
    
        for c in range(1,10):
            doser_names.append(dfi[f"md_Dosername_{c}"][i]if dfi[f"md_Dosername_{c}"][i] not in doser_names  else f"Doser {c}")
            dozezone.append(dfi[f"rd_DoseZone_{c-1}"][i])
            ecafter.append(dfi[f"rd_EC_After_{c-1}"][i])
            ecafter2.append(fl(dfi[f"rd_EC_After_{c-1}"][i]))#для определения максимума
            dosevol.append(dfi[f"md_dozevol_{c}"][i])
            ecr.append(dfi[f"md_ECr_{c}"][i])
        list_of_tuples = list(zip(dozezone,ecafter,dosevol,ecr))#обьединение списков в столбцы таблички
        df = pd.DataFrame(list_of_tuples).transpose()#повернуть таблицу тк она заполнена по вертикали а надо по горизонтали
        df.columns=doser_names
        maxec=max(ecafter2)#тут находим максимум списка данных рецепта
        #КОНФИГУРИРОВАНИЕ ЗАГОЛОВКА данных для ТАБЛИЧКИ
        df["Измерение"]=["Рецепт,мл/л","EC рецепт ms/m3","Обьем удобрений","EC расчитаное"]
        column_config={}
    #начало отрисовки данных замеса
        for j in df.columns:
            column_config[j]={'alignment': 'center'}
        info_exp.header(f"{dfi['farm'][i]} Зона {dfi['zonename'][i]} ")
        info_exp.text(f"Часовой пояс {st.session_state['farmconf'][dfi['farm'][i]]['timezone']}")
        delta=dfi['end_mix'][i]-dfi['start_mix'][i]
        if dfi['rd_nCycle'][i]!=dfi['rd_Cycle'][i]:
            info_exp.text(f"Замес {dfi['rd_nCycle'][i]:.0f} из {dfi['rd_Cycle'][i]:.0f}") 
        else:
            info_exp.text(f"Первый замес со сливом зоны")
        info_exp.text(f"Старт замеса {tzcnv(dfi['start_mix'][i])} залив в зону {tzcnv(dfi['end_mix'][i])} итого {delta.seconds // 3600 }ч {(delta.seconds % 3600)//60}м {(delta.seconds % 60)}сек"  )
        #рендер подготовленой таблички
        t=info_exp.dataframe(df,column_config=column_config,hide_index=True)
    # info_exp.header("Параметры замеса")
        #рендер трех столбцов с measurments
    



        col=   info_exp.columns(4)
        with col[0]:
            col[0].metric(f"Обьем замеса ", f"{dfi['md_Volume'][i]} л.")
            col[0].metric(f"Значение осмоса", f"{dfi['md_ECWater'][i]} ms/cm³")
        with col[1]:
            col[1].metric(f"⚡EC в баке",f"{dfi['md_ECTank'][i]} ms/cm",pc( dfi['md_ECTank'][i],maxec,"от рецепта"),help="Отображает так же разницу от значения рецепта")   
            col[1].metric(f"⚡EC 20 мин после налива",f"{dfi['rd_ECStart'][i]} ms/cm", delta=pc( dfi['rd_ECStart'][i],maxec,"от рецепта"))   
            col[1].metric(f"⚡EC на конец замеса",f"{dfi['md_ECmix'][i]} ms/cm", delta = pc( dfi['md_ECmix'][i],dfi['md_ECTank'][i],"от бака"),help="Отображает так же разницу между значением в баке и значением на конец замеса"  )   
        with col[2]:
            col[2].metric(f"🚰pH рецепта",f"{dfi['rd_pH_Zone'][i]}")    
            col[2].metric(f"🚰pH на конец замеса",f"{dfi['md_pHmix'][i]}",delta=pc(dfi['md_pHmix'][i],dfi['rd_pH_Zone'][i],"от рецепта") )   
        with col[3]:
            if dfi['rd_AutomateCorr'][i]==1:
                col[3].metric("Автоматическая коррекция","ON",)
                col[3].metric(f"Коэфф корректировки",f"{dfi['md_K_correct'][i]}")
                col[3].metric(f"Обьем зоны ",f"{dfi['rd_V_irrigation'][i]} л.")  
            else:
                col[3].metric("Автоматическая коррекция","OFF")
                col[3].metric(f"корректировочный множитель kEC ",f"{dfi['rd_KEC'][i]}")
                col[3].metric(f"корректировочный KpH",dfi['rd_KpH'][i])  
    
             #вывод графика 
        info_exp.write("График EC за неделю")  
        dfg,dfp,angle=getgraphdata(dfi['farm'][i],dfi['zone'][i])
    #    #
    #     merged_df = pd.merge(dfp, dfg, on='ts')
    #     info_exp.dataframe(merged_df)
    #     source1 = ColumnDataSource(data=dict(x=merged_df['ts'], y=merged_df['val_x']))
    #     source2 = ColumnDataSource(data=dict(x=merged_df['ts'], y=merged_df['val_y']))
    #     p1= figure(
    #                         title='Недельный график',
    #                         x_axis_label='time',
    #                         y_axis_label='EC')

    #     p1.line(x='x', y='y', source=source1, line_width=2, legend_label='EC')
    #     p2= figure(
    #                         title='полином',
    #                         x_axis_label='time',
    #                         y_axis_label='EC')

    #     p2.line(x='x', y='y', source=source2, line_width=2, color='red', legend_label='poly')
    #     plots = gridplot([[p1], [p2]], sizing_mode='stretch_both')

    #     info_exp.bokeh_chart(plots) """
        info_exp.line_chart(data=dfg,x='ts',y='val',)
       # info_exp.line_chart(data=dfp,x='ts',y='val',)
        info_exp.write(f"Угол наклона графика за последние 3 дня {angle}")
        #info_exp.line_chart(data=merged_df,x='ts',y='val')  # val_x и val_y - значения из dfg и dfg3 соответственно
        #вывод лога
        dfl=getlogdata(dfi['farm'][i],tzcnv(dfi['start_mix'][i]),tzcnv(dfi['end_mix'][i]))
        info_exp.write("Лог замеса") 
        info_exp.data_editor(dfl,hide_index=True,width=800)
        
    if st.session_state["authentication_status"] and not df is None:                    
        dfi=df.query("farm==@farms & zonename==@zones")

        #вывод фильтрованой основной таблицы и в сайдбаре - кнопок конкретных замесов
        #st.expander("данные запроса",expanded=False).data_editor(dfi)
        st.sidebar.header("Замесы с указанными параметрами")
        sidebutton={}

        def filter(i):
            st.session_state['selected']=i
            st.session_state['timezone']=st.session_state["farmconf"].get(dfi["farm"][i])['timezone']


        def badlabel(i)->str:
            def badpc(a,b,w,h)->str:
                "вспомогательная функция для вывода дельты в процентах"
                try:
                    buf= (1-b/a)*100 
                    if buf>h:
                       return  ":exclamation: "
                    if buf>w:
                       return ":question: "
                    return ":ok: "
                except:
                    return ""


            maxec=max([fl(dfi[f"rd_EC_After_{c}"][i]) for c in range(10)])
            buf=badpc(dfi['rd_ECStart'][i],maxec,12,15),badpc(dfi['md_ECTank'][i],maxec,12,15),badpc(dfi['md_ECmix'][i],dfi['md_ECTank'][i],12,15)
            if  ":exclamation: " in buf:
                return ":exclamation: "
            if  ":question: " in buf:
                return ":question: "
            return   ":ok: "       

            
        if 'selected' in st.session_state.keys():
            button_on_click(st.session_state['selected'])
        for i in dfi.index:
            sidebutton[i]=st.sidebar.button(f"{badlabel(i)}{dfi['farm'][i]} Замес {tzcnv(dfi.start_mix[i])} зона {dfi.zonename[i]:} : {dfi.rd_nCycle[i]:.0f} из {dfi.rd_Cycle[i]:.0f}",on_click=filter,args=[i],key=f"sb{i}",use_container_width=True)
    

    

           
   
# '''
# if __name__ == '__main__':
#     if runtime.exists():
#         main()
#     else:
#         sys.argv = ["streamlit", "run","--server.port","8000", sys.argv[0]]
#         sys.exit(stcli.main())
#         '''