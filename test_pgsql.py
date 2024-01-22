import sys
from streamlit.web import cli as stcli
import streamlit as st
from streamlit import runtime
import datetime    
import pandas as pd
from icecream import ic
from sqlalchemy import URL,create_engine

today = datetime.datetime.now()
yesterday= today+datetime.timedelta(days=-1)


@st.cache_data
def datechange(dat:tuple)->pd.DataFrame:
  
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

    url_object = URL.create(
    "mysql+pymysql",
    username="scadauser",
    password="3a8AWur6H2",  # plain (unescaped) text
    host="10.10.0.251",
    database="testdemo",
    )
    engine= create_engine(url_object,echo=True)
    with engine.connect() as conn, conn.begin():  
        df = pd.read_sql_query(f"SELECT * FROM mixdata where `start_mix` BETWEEN '{dt_b}' AND '{dt_e}'", conn)  
        return df
    # ic(data)

    
#def main():

st.set_page_config(page_title='Информация о замесах',
                    page_icon=":bar_chart:",
                    layout="wide"
                    )
     
st.sidebar.header("Фильтр")





intdates=st.sidebar.date_input(label="Выберите диапазон дат",
    value=(yesterday,today),min_value=None,max_value=None,
    format="DD.MM.YYYY",
) 
df=datechange(intdates)  
if not df is None:
    farms=st.sidebar.multiselect("Фермы",
                            options=df["farm"].unique(),
                            default=df["farm"].unique()
                            ) 
    zones=st.sidebar.multiselect("зоны",
                            options=df["zone"].unique(),
                            default=df["zone"].unique()
                            ) 
    #info_exp=st.expander("Информация о замесе")
    def button_on_click(i):
        info_exp=st.expander("Информация о замесе",expanded=True)
        doser_names=["Измерение"]
        dozezone=[""]
        ecafter=[""]
        dosevol=[""]
        ecr=[""]
        df=pd.DataFrame()

        
 
        for c in range(1,10):
            doser_names.append(dfi[f"md_Dosername_{c}"][i]if dfi[f"md_Dosername_{c}"][i]!="none" else f"Doser {c}")
            dozezone.append(dfi[f"rd_DoseZone_{c-1}"][i])
            ecafter.append(dfi[f"rd_EC_After_{c-1}"][i])
            dosevol.append(dfi[f"md_dozevol_{c}"][i])
            ecr.append(dfi[f"md_ECr_{c}"][i])
        list_of_tuples = list(zip(dozezone,ecafter,dosevol,ecr))
        df = pd.DataFrame(list_of_tuples).transpose()
        df.columns=doser_names
      
        df["Измерение"]=["Рецепт,мл/л","EC рецепт ms/m3","Обьем удобрений","EC расчитаное"]
    
        #df.style.hide(axis="index")
        column_config={}
       
        for i in df.columns:
            column_config[i]={'alignment': 'center'}
       
        t=info_exp.dataframe(df,hide_index=True,column_config=column_config)
      

    dfi=df.query("farm==@farms & zone==@zones")
    st.data_editor(dfi)
    st.sidebar.header("Замесы с указанными параметрами")
    for i in dfi.index:
        st.sidebar.button(f"Замес {str(dfi.start_mix[i])} зона {dfi.zone[i]:.0f} : {dfi.rd_nCycle[i]:.0f} из {dfi.rd_Cycle[i]:.0f}",on_click=button_on_click,args=[i])
   

    

           
   
# '''
# if __name__ == '__main__':
#     if runtime.exists():
#         main()
#     else:
#         sys.argv = ["streamlit", "run","--server.port","8000", sys.argv[0]]
#         sys.exit(stcli.main())
#         '''