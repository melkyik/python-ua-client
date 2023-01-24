import json

#j=json.loads('{"backendUrl":"http://admin.ifarmproject.com:3000","opcEndpoint":{"host":"10.10.13.30","port":4840,"path":"/","security":{"type":"NONE","policy":"http://opcfoundation.org/UA/SecurityPolicy#None","enabled":true,"userName":"admin","password":"wago1"}},"timeout":60000,"sessionTimeout":3600000,"logFilename":"Berdsk.log","maxBatchSize":100}')
j=json.loads("{\"backendUrl\":\"http://admin.ifarmproject.com:3000\",\"opcEndpoint\":{\"host\":\"10.10.13.30\",\"port\":4840,\"path\":\"/\",\"security\":{\"type\":\"NONE\",\"policy\":\"http://opcfoundation.org/UA/SecurityPolicy#None\",\"enabled\":true,\"userName\":\"admin\",\"password\":\"wago1\"}},\"timeout\":60000,\"sessionTimeout\":3600000,\"logFilename\":\"Berdsk.log\",\"maxBatchSize\":100}")
print(type(j))
