import logging
import asyncio

from asyncua import Client, ua, Node


_logger = logging.getLogger(__name__)


class SubHandler:
    """
    Subscription Handler. To receive events from server for a subscription
    This class is just a sample class. Whatever class having these methods can be used
    """

    def datachange_notification(self, node: Node, val, data):
        """
        called for every datachange notification from server
        """ 
        
        print("ЗНАЧЕНИЕ СМЕНИЛОСЬ НА ", val)
        
        _logger.info("datachange_notification %r %s", node, val)

    def event_notification(self, event: ua.EventNotificationList):
        """
        called for every event notification from server
        """
        pass

    def status_change_notification(self, status: ua.StatusChangeNotification):
        """
        called for every status change notification from server
        """
        _logger.info("status_notification %s", status)

async def main():
    handler = SubHandler()

    while True:
        client = Client(url="opc.tcp://10.10.2.244:4840")
        client.set_user("admin")
        client.set_password("wago")
        try:
            async with client:
                _logger.warning("Connected")
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
                node = (Node(client,'ns=4;s=|var|WAGO 750-8212 PFC200 G2 2ETH RS.Application.PLC_PRG.counter'),)
                
                #пример простое чтение данных при запуске
                struct = client.get_node("ns=4;s=|var|WAGO 750-8212 PFC200 G2 2ETH RS.Application.PLC_PRG.counter")
                var = await struct.read_value()
                print("ЗНАЧЕНИЕ=", var)
        
                await subscription.subscribe_data_change(node)
         
                while True:
                    await asyncio.sleep(1)
                    await client.check_connection()  # Throws a exception if connection is lost
        except (ConnectionError, ua.UaError):
            _logger.warning("Reconnecting in 2 seconds")
            await asyncio.sleep(2)

if __name__ == "__main__":

    logging.basicConfig(level=logging.INFO)
    asyncio.run(main())
