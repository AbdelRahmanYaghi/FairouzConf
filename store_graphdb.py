import json 
from GraphEmbedder.functions import tracks_to_graphdb

data = json.load(open(r'C:\Users\Glazed\Documents\GitHub\FairouzConf\tracks.json'))

tracks_to_graphdb(data)
