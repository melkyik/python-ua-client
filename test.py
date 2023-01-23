import asyncio
import asyncpg
import datetime

async def get_farm_settings()->list:
        """считывание параметров связи для фермы""" 
        query= "SELECT scada_settings.title\
                ,scada_settings.settings\
                FROM scada inner join scada_settings on scada.setting_id = scada_settings.id\
                where status='active'"
        s=await conn.fetch(query) 
        await conn.close()
        return s                
    # Close the connection.

       
async def main():
    # Establish a connection to an existing database named "test"
    # as a "postgres" user.
    _conn = await asyncpg.connect(user="igor",
                                        # пароль, который указали при установке PostgreSQL
                                        password="adminsa",
                                        host="10.10.2.152",
                                        port="5432",
                                        database="ifarm")

    conn:asyncpg.connection.Connection =_conn #чтобы работал спелчек
    # Select a row from the table.
    row = await conn.fetchrow("SELECT version();")
    if _conn:
        query = "SELECT scada_settings.title\
                ,scada_settings.settings\
                FROM scada inner join scada_settings on scada.setting_id = scada_settings.id\
                where status='active'"
    q=await conn.fetch(query) 
    # *row* now contains
    # asyncpg.Record(id=1, name='Bob', dob=datetime.date(1984, 3, 1))
    for k in q:
        print(k[0])




asyncio.get_event_loop().run_until_complete(main())