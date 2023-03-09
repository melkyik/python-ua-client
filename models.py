from pydantic import BaseModel,Field
from datetime import datetime
from typing import Optional,List,Dict,Any

class Point(BaseModel):
    name: str =Field(...,description="Имя точки")
    baseId: str = Field(...,description="ID точки в базе")
    addr: str = Field(...,description="Короткий адрес точки в базе")
    oldval: Any = Field(...,description="Предыдущее значение")
    value: Any =Field(...,description="последнее значение")
    status: bool =Field(...,description="значение в норме")
    plcdate: datetime =Field(...,description="Дата обновления точки")
    archve: bool=Field(...,description="Архивация")
    readed_node_full_name: str= Field(...,description="Полный адрес точки")


class RespFarm(BaseModel):
    id: str =       Field(...,description="ID фермы")
    name: str =     Field(...,description="имя фермы")
    Сonnection: str =Field(...,description="Статус подключения")
    values: Dict[str,Point]
   