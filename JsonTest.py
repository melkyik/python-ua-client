import json
#from io import FileIO;
configfile  =   open("config.json")
configdata    =   json.load(configfile)
configfile.close()
pointfile   = open("standartpoints.json")
pointdata  = dict(json.load(pointfile))
pointfile.close()

#for i in configdata['device']:
#    print(i)
print(pointdata)
s =dict
for i in pointdata['Tag']:
    print(i["address"])
    if  pointdata.  ['dd']: print