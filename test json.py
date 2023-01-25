import json
def allfarminfo():
    js=list()
    for k in farms.farms:
        js.append(js["id"]["connection"]="3")
        js["id"]["connection"]="3"
       #for v in farms.get(k).Value:
        #    js["id"]["values"][farms.get(k).getTagByShort(v).name]=farms.get(k).getValueShort(v)
                
    return json.dumps(js , indent=2)
#j=json.loads('{"backendUrl":"http://admin.ifarmproject.com:3000","opcEndpoint":{"host":"10.10.13.30","port":4840,"path":"/","security":{"type":"NONE","policy":"http://opcfoundation.org/UA/SecurityPolicy#None","enabled":true,"userName":"admin","password":"wago1"}},"timeout":60000,"sessionTimeout":3600000,"logFilename":"Berdsk.log","maxBatchSize":100}')
j=json.loads("{\"backendUrl\":\"http://admin.ifarmproject.com:3000\",\"opcEndpoint\":{\"host\":\"10.10.13.30\",\"port\":4840,\"path\":\"/\",\"security\":{\"type\":\"NONE\",\"policy\":\"http://opcfoundation.org/UA/SecurityPolicy#None\",\"enabled\":true,\"userName\":\"admin\",\"password\":\"wago1\"}},\"timeout\":60000,\"sessionTimeout\":3600000,\"logFilename\":\"Berdsk.log\",\"maxBatchSize\":100}")
print(json.dumps(j, indent=2))
config = uvicorn.Config("test_pgsql:app", port=8000, log_level="info")
server = uvicorn.Server(config) 