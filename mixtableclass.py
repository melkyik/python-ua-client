from sqlalchemy import create_engine,ForeignKey,Column,String,TIMESTAMP,Float,Integer,Boolean,URL
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker

Base=declarative_base()
class MixData(Base):
    __tablename__="mixdata"
    id              =Column("id",Integer,autoincrement="auto", primary_key=True)
    farm            =Column("farm",       String(50),index=True)
    start_mix       =Column("start_mix",    TIMESTAMP)
    "начало замеса"
    end_mix         =Column("end_mix",    TIMESTAMP)
    "конец замеса"
    result          =Column("result",       String(200))
    "результат замеса"
    zone            =Column("zone",       Integer)
    "номер зоны"
    rd_Automate     =Column("rd_Automate",  Boolean)
    "автоматический режим включен"
    rd_AutomateCorr =Column("rd_AutomateCorr",   Boolean)
    "автоматическая коррекция включена"
    rd_Cycle        =Column("rd_Cycle",   Float) 
    "количество циклов"
    rd_nCycle       =Column("rd_nCycle",   Float) 
    "текущий цикл замеса"
    rd_K            =Column("rd_K",   Float)
    "коэффициент коррекции" 
    
    rd_KEC          =Column("rd_KEC",   Float) 
    "коэффициент коррекции EC" 
    rd_KpH          =Column("rd_KpH",   Float)
    "коэффициент коррекции pH"  
    rd_pH_Zone          =Column("rd_pH_Zone",   Float)
    " pH рецепта"  
    rd_V_irrigation =Column("rd_V_irrigation",   Float)
    "обьем бака ирригации" 
    md_pHmix            =Column("md_pHmix",          Float,default=None)
    md_ECmix            =Column("md_ECmix",          Float,default=None)

#новые столбцы
    md_Volume          =Column("md_Volume",          Float,default=None)
    "обьем налитой жидкости"
    md_ECWater         =Column("md_ECWater",         Float,default=None)
    "EC осмоса изначальный"
    md_ECTank            =Column("md_ECTank",         Float,default=None)
    "EC в баке на начало замеса"
    rd_ECStart          =Column("rd_ECStart",         Float,default=None)
    "сохраненый EC через 20 минут после инициализированного налива"
    md_K_correct           =Column("md_K_correct",         Float,default=None)
    "коэффициент корректировки расчитанный"
    zonename=Column("zonename",       String(5),default=None)
#-----------------------

    rd_DoseZone_0 = Column("rd_DoseZone_0", Float, default=None)
    rd_DoseZone_1 = Column("rd_DoseZone_1", Float, default=None)
    rd_DoseZone_2 = Column("rd_DoseZone_2", Float, default=None)
    rd_DoseZone_3 = Column("rd_DoseZone_3", Float, default=None)
    rd_DoseZone_4 = Column("rd_DoseZone_4", Float, default=None)
    rd_DoseZone_5 = Column("rd_DoseZone_5", Float, default=None)
    rd_DoseZone_6 = Column("rd_DoseZone_6", Float, default=None)
    rd_DoseZone_7 = Column("rd_DoseZone_7", Float, default=None)
    rd_DoseZone_8 = Column("rd_DoseZone_8", Float, default=None)
    rd_DoseZone_9 = Column("rd_DoseZone_9", Float, default=None)

    rd_EC_After_0 = Column("rd_EC_After_0", Float, default=None)
    rd_EC_After_1 = Column("rd_EC_After_1", Float, default=None)
    rd_EC_After_2 = Column("rd_EC_After_2", Float, default=None)
    rd_EC_After_3 = Column("rd_EC_After_3", Float, default=None)
    rd_EC_After_4 = Column("rd_EC_After_4", Float, default=None)
    rd_EC_After_5 = Column("rd_EC_After_5", Float, default=None)
    rd_EC_After_6 = Column("rd_EC_After_6", Float, default=None)
    rd_EC_After_7 = Column("rd_EC_After_7", Float, default=None)
    rd_EC_After_8 = Column("rd_EC_After_8", Float, default=None)
    rd_EC_After_9 = Column("rd_EC_After_9", Float, default=None)

    md_ECr_0 = Column("md_ECr_0", Float, default=None)
    md_ECr_1 = Column("md_ECr_1", Float, default=None)
    md_ECr_2 = Column("md_ECr_2", Float, default=None)
    md_ECr_3 = Column("md_ECr_3", Float, default=None)
    md_ECr_4 = Column("md_ECr_4", Float, default=None)
    md_ECr_5 = Column("md_ECr_5", Float, default=None)
    md_ECr_6 = Column("md_ECr_6", Float, default=None)
    md_ECr_7 = Column("md_ECr_7", Float, default=None)
    md_ECr_8 = Column("md_ECr_8", Float, default=None)
    md_ECr_9 = Column("md_ECr_9", Float, default=None)

    md_dozevol_0 = Column("md_dozevol_0", Float, default=None)
    md_dozevol_1 = Column("md_dozevol_1", Float, default=None)
    md_dozevol_2 = Column("md_dozevol_2", Float, default=None)
    md_dozevol_3 = Column("md_dozevol_3", Float, default=None)
    md_dozevol_4 = Column("md_dozevol_4", Float, default=None)
    md_dozevol_5 = Column("md_dozevol_5", Float, default=None)
    md_dozevol_6 = Column("md_dozevol_6", Float, default=None)
    md_dozevol_7 = Column("md_dozevol_7", Float, default=None)
    md_dozevol_8 = Column("md_dozevol_8", Float, default=None)
    md_dozevol_9 = Column("md_dozevol_9", Float, default=None)

    md_Dosername_0 = Column("md_Dosername_0", String(20), default=None)
    md_Dosername_1 = Column("md_Dosername_1", String(20), default=None)
    md_Dosername_2 = Column("md_Dosername_2", String(20), default=None)
    md_Dosername_3 = Column("md_Dosername_3", String(20), default=None)
    md_Dosername_4 = Column("md_Dosername_4", String(20), default=None)
    md_Dosername_5 = Column("md_Dosername_5", String(20), default=None)
    md_Dosername_6 = Column("md_Dosername_6", String(20), default=None)
    md_Dosername_7 = Column("md_Dosername_7", String(20), default=None)
    md_Dosername_8 = Column("md_Dosername_8", String(20), default=None)
    md_Dosername_9 = Column("md_Dosername_9", String(20), default=None)
    
    


    def __init__(
        self,
        start_mix=None,
        end_mix=None,
        result=None,
        farm=None,
        zone=None,
        zonename=None,
        rd_Automate=None,
        rd_AutomateCorr=None,
        rd_Cycle=None,
        rd_nCycle=None,
        rd_K=None,
        rd_KEC=None,
        rd_KpH=None,
        rd_pH_Zone=None,
        rd_V_irrigation=None,
        rd_DoseZone_0=None,
        rd_DoseZone_1=None,
        rd_DoseZone_2=None,
        rd_DoseZone_3=None,
        rd_DoseZone_4=None,
        rd_DoseZone_5=None,
        rd_DoseZone_6=None,
        rd_DoseZone_7=None,
        rd_DoseZone_8=None,
        rd_DoseZone_9=None,
        rd_EC_After_0=None,
        rd_EC_After_1=None,
        rd_EC_After_2=None,
        rd_EC_After_3=None,
        rd_EC_After_4=None,
        rd_EC_After_5=None,
        rd_EC_After_6=None,
        rd_EC_After_7=None,
        rd_EC_After_8=None,
        rd_EC_After_9=None,
        md_ECr_0=None,
        md_ECr_1=None,
        md_ECr_2=None,
        md_ECr_3=None,
        md_ECr_4=None,
        md_ECr_5=None,
        md_ECr_6=None,
        md_ECr_7=None,
        md_ECr_8=None,
        md_ECr_9=None,
        md_dozevol_0=None,
        md_dozevol_1=None,
        md_dozevol_2=None,
        md_dozevol_3=None,
        md_dozevol_4=None,
        md_dozevol_5=None,
        md_dozevol_6=None,
        md_dozevol_7=None,
        md_dozevol_8=None,
        md_dozevol_9=None,
        md_Dosername_0=None,
        md_Dosername_1=None,
        md_Dosername_2=None,
        md_Dosername_3=None,
        md_Dosername_4=None,
        md_Dosername_5=None,
        md_Dosername_6=None,
        md_Dosername_7=None,
        md_Dosername_8=None,
        md_Dosername_9=None,
        md_pHmix=None,
        md_ECmix=None,
        md_Volume=None,
        md_ECWater=None,
        md_ECTank=None,
        rd_ECStart=None,
        md_K_correct =None,

    ):
        self.start_mix = start_mix
        self.end_mix = end_mix
        self.result = result
        self.farm=farm
        self.zone=zone
        self.zonename=zonename
        self.rd_Automate = rd_Automate
        self.rd_AutomateCorr = rd_AutomateCorr
        self.rd_Cycle = rd_Cycle
        self.rd_nCycle = rd_nCycle
        self.rd_K = rd_K
        self.rd_KEC = rd_KEC
        self.rd_KpH = rd_KpH
        self.rd_pH_Zone=rd_pH_Zone
        self.rd_V_irrigation = rd_V_irrigation
        self.rd_DoseZone_0 = rd_DoseZone_0
        self.rd_DoseZone_1 = rd_DoseZone_1
        self.rd_DoseZone_2 = rd_DoseZone_2
        self.rd_DoseZone_3 = rd_DoseZone_3
        self.rd_DoseZone_4 = rd_DoseZone_4
        self.rd_DoseZone_5 = rd_DoseZone_5
        self.rd_DoseZone_6 = rd_DoseZone_6
        self.rd_DoseZone_7 = rd_DoseZone_7
        self.rd_DoseZone_8 = rd_DoseZone_8
        self.rd_DoseZone_9 = rd_DoseZone_9
        self.rd_EC_After_0 = rd_EC_After_0
        self.rd_EC_After_1 = rd_EC_After_1
        self.rd_EC_After_2 = rd_EC_After_2
        self.rd_EC_After_3 = rd_EC_After_3
        self.rd_EC_After_4 = rd_EC_After_4
        self.rd_EC_After_5 = rd_EC_After_5
        self.rd_EC_After_6 = rd_EC_After_6
        self.rd_EC_After_7 = rd_EC_After_7
        self.rd_EC_After_8 = rd_EC_After_8
        self.rd_EC_After_9 = rd_EC_After_9
        self.md_ECr_0 = md_ECr_0
        self.md_ECr_1 = md_ECr_1
        self.md_ECr_2 = md_ECr_2
        self.md_ECr_3 = md_ECr_3
        self.md_ECr_4 = md_ECr_4
        self.md_ECr_5 = md_ECr_5
        self.md_ECr_6 = md_ECr_6
        self.md_ECr_7 = md_ECr_7
        self.md_ECr_8 = md_ECr_8
        self.md_ECr_9 = md_ECr_9
        self.md_dozevol_0 = md_dozevol_0
        self.md_dozevol_1 = md_dozevol_1
        self.md_dozevol_2 = md_dozevol_2
        self.md_dozevol_3 = md_dozevol_3
        self.md_dozevol_4 = md_dozevol_4
        self.md_dozevol_5 = md_dozevol_5
        self.md_dozevol_6 = md_dozevol_6
        self.md_dozevol_7 = md_dozevol_7
        self.md_dozevol_8 = md_dozevol_8
        self.md_dozevol_9 = md_dozevol_9
        self.md_Dosername_0 = md_Dosername_0
        self.md_Dosername_1 = md_Dosername_1
        self.md_Dosername_2 = md_Dosername_2
        self.md_Dosername_3 = md_Dosername_3
        self.md_Dosername_4 = md_Dosername_4
        self.md_Dosername_5 = md_Dosername_5
        self.md_Dosername_6 = md_Dosername_6
        self.md_Dosername_7 = md_Dosername_7
        self.md_Dosername_8 = md_Dosername_8
        self.md_Dosername_9 = md_Dosername_9
 
        self.md_pHmix = md_pHmix
        self.md_ECmix = md_ECmix

        self.md_Volume=md_Volume,
        self.md_ECWater=md_ECWater,
        self.md_K_correct =md_K_correct,
        self.md_ECTank=md_ECTank,
        self.rd_ECStart=rd_ECStart,

    def __repr__(self):
        return f"{self.id} start={self.start_mix}, end={self.end_mix}"
    
# url_object = URL.create(
#             "mysql+pymysql",
#             username="scadauser",
#             password="3a8AWur6H2",  # plain (unescaped) text
#             host="10.10.0.251",
#             database="testdemo",
#         )
        
# engine= create_engine(url_object,echo=True)    
# Base.metadata.create_all(bind=engine)

