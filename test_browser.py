import asyncio
import logging
from asyncua import Client, Node, ua

logging.basicConfig(level=logging.WARNING)
_logger = logging.getLogger('asyncua')


async def browse_nodes(node: Node,l:int=0):
    """
    Build a nested node tree dict by recursion (filtered by OPC UA objects and variables).
    """
    maxlevel=2
    node_class = await node.read_node_class()
    children = []
    child:Node
    strchildren:list[str]=[]
    print ("node=",node)
    for child in await node.get_children():
        if await child.read_node_class() in [ua.NodeClass.Object, ua.NodeClass.Variable]:
            if l <= maxlevel :
                children.append(await browse_nodes(child,l=l+1))
            else:
                children.append(child)                     
            strchildren.append(str(child))
            print ("child=",child)
    if node_class != ua.NodeClass.Variable:
        var_type = None
    else:
        try:
            var_type = (await node.read_data_type_as_variant_type()).value
        except ua.UaError:
            _logger.warning('Node Variable Type could not be determined for %r', node)
            var_type = None
    return {
        'id': str(node),
        'name': (await node.read_display_name()).Text,
        'cls': node_class.value,
        'children':str( strchildren),
        'type': var_type,
    }


async def task(loop):
    url = "opc.tcp://10.10.2.30:4840"
    # url = "opc.tcp://localhost:4840/freeopcua/server/"
    try:
        client = Client(url=url)
        client.set_user('admin')
        client.set_password('wago1')
        # client.set_security_string()
        await client.connect()
        # Client has a few methods to get proxy to UA nodes that should always be in address space such as Root or Objects
        root = client.get_node("ns=4;s=|var|WAGO 750-8212 PFC200 G2 2ETH RS.Application.GVL.RecipesStruct")
        print("Objects node is:", root)

        # Node objects have methods to read and write node attributes as well as browse or populate address space
        print("Children of root are:", await root.get_children())

        tree = await browse_nodes(root)
        print('Node tree: %r', tree)
    except Exception:
        _logger.exception('error')
    finally:
        await client.disconnect()


def main():
    loop = asyncio.get_event_loop()
    loop.set_debug(True)
    loop.run_until_complete(task(loop))
    loop.close()


if __name__ == "__main__":
    main()