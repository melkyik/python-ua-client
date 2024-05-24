import pandas as pd
import numpy as np
import plotly.express as px
import os
import io
import requests
from PIL import Image
from icecream import ic
from dotenv import load_dotenv
from os.path import join, dirname
from telegram import Bot,Message
from sqlalchemy import URL,create_engine
from typing import Tuple
import plotly.graph_objects as go
from zoneinfo import ZoneInfo
from pandas import Timestamp
import datetime


dotenv_path = join(dirname(__file__), '.env')
load_dotenv(dotenv_path)


def extzcn(t: Timestamp, to="Asia/Novosibirsk") -> datetime.datetime:
    "конвертирует таймстамп в datetime с часовым поясом на вводе только UTC"
    buf = t.to_pydatetime().astimezone(ZoneInfo(to))
    return buf


def send_to_bot(message,photo_bytes :io.BytesIO=None)->Message:
   "посылка сообщения в  группу "
   chat_id=os.environ.get("GROUP_ID")
   bot=Bot(token=os.environ.get("BOT_TOKEN")) 
   if photo_bytes  is None:
       return bot.send_message(chat_id=chat_id,text=message,parse_mode="HTML")
   else:
        photo_bytes.seek(0)
        bot.send_photo(chat_id=chat_id, photo=photo_bytes ,caption=message,parse_mode="HTML")

       




def getlastmixes(farmname,zonename,n=3,tz="UTC")->Tuple[pd.DataFrame,float]:

    url_object = URL.create(
                "mysql+pymysql",
                username=os.environ.get("MIXDB_USER"),
                password=os.environ.get("MIXDB_PASSWORD"),  # plain (unescaped) text
                host=os.environ.get("MIXDB_HOST"),
                database=os.environ.get("MIXDB_BASE"),
            )
    engine= create_engine(url_object,echo=True)

    with engine.connect() as conn, conn.begin():   
        df = pd.read_sql_query(f"SELECT md_ECTank,end_mix FROM mixdata WHERE farm='{farmname}' AND zonename='{zonename}' ORDER BY end_mix DESC LIMIT {n}", conn) 
        df_inverted = df[::-1].reset_index(drop=True)
        x = df_inverted.index.values
        y = df_inverted.md_ECTank.values
        coefficients = np.polyfit(x,y,1)
        poly = np.poly1d(coefficients)
        derivative = np.polyder(poly)
        derivative_values = derivative(0)
        res = round(np.rad2deg(np.arctan(derivative_values)),3)
        df_inverted["poly"]=poly(x)

        return df_inverted,res
    
 

def make_graph(farmname,zonename,maxec,n,tz="UTC")->io.BytesIO:
    
    df,angle=getlastmixes(farmname,zonename,n,tz)

    df['end_mix'] = pd.to_datetime(df['end_mix']).dt.tz_localize('UTC').dt.tz_convert(ZoneInfo(tz))
    #залупа в том что выше процедурка работает только с UTC и на графике отображается локальное время фермы!
    # если совмещать с реальным графиком то у него будет местное время , это нужно учесть
    # Создаем график с plotly express
    fig = px.line(df, x=df.index, y=['md_ECTank', 'poly'], labels={'index': 'index', 'value': 'EC'},                  
                  title=f'{farmname} зона {zonename} \nПоследние {n} замеса. Угол={angle}',
                  template="plotly_dark")  # Используем темный шаблон
    fig.update_traces(mode="lines+markers") 
   
    fig.update_yaxes(range=[None, 3.5])  # Установка максимального значения по оси y
    fig.add_hline(y=maxec, line_dash="dot", line_color="red", annotation_text=f"Contol EC: {maxec:.2f}", annotation_position="bottom right")
  #  fig.add_trace(go.Scatter(x=df.end_mix, y=df['md_ECTank'], mode='markers+text', text=df.end_mix, textposition='top center', marker_symbol='circle-open'))

    # Сохраняем график как изображение
    img_bytes = fig.to_image(format="png",width=800, height=450)
    img = Image.open(io.BytesIO(img_bytes))
    photo_bytes = io.BytesIO()
    img.save(photo_bytes, format='PNG')
    return photo_bytes
         
 
    
if __name__=="__main__":

    t=Timestamp('2024-04-23 12:53:31+1000', tz='Asia/Vladivostok')
    ic(t)
    ic(extzcn(t))
    send_to_bot("test",make_graph("Blagoveshensk FU1","C",2.34,3,tz="Asia/Vladivostok")  ) 