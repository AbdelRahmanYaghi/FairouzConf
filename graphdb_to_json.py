'''
This script is used to convert 
 the graphdb nodes to a json file,
 named 'tracks.json'.
'''

from GraphEmbedder.functions import get_graphdb_nodes, tracks_to_ttl
import json

json.dump(get_graphdb_nodes(), open('tracks.json', 'w'), indent=4)
