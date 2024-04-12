from mixtableclass import MixData 
from icecream import ic
def fl(a):
    try:
        return float(a)
    except:
        return 0
row=MixData(       
                                                rd_EC_After_0       ="666.000",
                                                rd_EC_After_1       ="fsf",
                                                rd_EC_After_2       =2,
                                                rd_EC_After_3       =3,
                                                rd_EC_After_4       =4,
                                                rd_EC_After_5       =5,
                                                rd_EC_After_6       =6,
                                                rd_EC_After_7       =7,
                                                rd_EC_After_8       =9,
                                                rd_EC_After_9       =77,
                                                 rd_ECStart       =22,
                                                  md_ECmix       =22
                                                        )
maxec=max([fl(vars(row)[f"rd_EC_After_{c}"]) for c in range(10)])
ic(maxec)
ic(row.rd_EC_After_1)
ic(row.rd_ECStart)
ic(row.md_ECmix)