import logging
import asyncio
import json
from asyncua import Client, ua, Node 

from asyncua.common.subscription import DataChangeNotif

mylogger = logging.getLogger("ifarm")


class SubHandler:
    """
    Subscription Handler. To receive events from server for a subscription
    This class is just a sample class. Whatever class having these methods can be used
    """
    """DataChangeNotification(<asyncua.common.subscription.SubscriptionItemData object at 0x000001D010B04F10>, 
        MonitoredItemNotification(ClientHandle=201, Value=DataValue(Value=Variant(Value=19.709999084472656, VariantType=<VariantType.Float: 10>, Dimensions=None, is_array=False), StatusCode_=StatusCode(value=0), SourceTimestamp=datetime.datetime(2023, 2, 8, 13, 58, 12, 245000), ServerTimestamp=datetime.datetime(2023, 2, 8, 13, 58, 12, 245000), SourcePicoseconds=None, ServerPicoseconds=None)))
    """
    async def datachange_notification(self, node: Node, val, data:DataChangeNotif):
         # called for every datachange notification from server
          #Node(data.subscription_data.client_handle,data.subscription_data.node)
        print("id",node.nodeid.Identifier, (data.subscription_data.node ))
        #mylogger.info("datachange_notification %r %s", node, val)
    def event_notification(self, event: ua.EventNotificationList):
       #called for every event notification from server
        pass
    def status_change_notification(self, status: ua.StatusChangeNotification):
        #called for every status change notification from server
       pass #mylogger.info("status_notification %s", status)

async def main():
    handler = SubHandler()

    while True:
        client = Client(url="opc.tcp://10.10.2.30:4840")
        client.set_user("admin")
        client.set_password("wago1")
        try:
            async with client:
                mylogger.warning("Connected")
                subscription = await client.create_subscription(500, handler)
                #определяем Node как список с единственным тегом
                
        # пример со списком тегов был описан тут
        #https://github.com/FreeOpcUa/opcua-asyncio/issues/1072
        # nodes_to_read = [
        #     'ns=4;s=|var|CODESYS Control Win V3 x64.Application.ioHMIControls.EStopHMI',
        #     'ns=4;s=|var|CODESYS Control Win V3 x64.Application.ioHMIControls.JogHMI',
        #     'ns=4;s=|var|CODESYS Control Win V3 x64.Application.ioHMIControls.RunHMI',
        #     'ns=4;s=|var|CODESYS Control Win V3 x64.Application.ioHMIControls.ThreadHMI',
        # ]
        # nodes_to_read = [Node(client, n) for n in nodes_to_read]
        # i=0
                ##ниже обязательно должен быть обьявлен список подписки, в примере он из одного блока
                node = (Node(client,'ns=4; s=|var|WAGO 750-8212 PFC200 G2 2ETH RS.Application.GVL.AIArray.AI[1].AIData.Value'),)
                
                #пример простое чтение данных при запуске
                struct = client.get_node("ns=4;s=|var|WAGO 750-8212 PFC200 G2 2ETH RS.Application.GVL.AIArray.AI[1].AIData.Value")
         
                #dv = ua.DataValue(ua.Variant(33, ua.VariantType.UInt16))
                #await struct.write_value(dv)
                print(f"ЗНАЧЕНИЕ={await struct.read_value()} доп { (await struct.read_data_value()).SourceTimestamp}")

             
                await subscription.subscribe_data_change(node)
         
                while True:
                    await asyncio.sleep(1)
                    await client.check_connection()  # Throws a exception if connection is lost
        except (ConnectionError, ua.UaError):
            mylogger.warning("Reconnecting in 2 seconds")
            await asyncio.sleep(2)

if __name__ == "__main__":
   
    logging.basicConfig(level=logging.WARNING)
    asyncio.run(main())
