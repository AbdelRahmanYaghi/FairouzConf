'''
This script creates the graph embeddings for
 the tracks in the dataset. It uses the node2vec
 algorithm to create the embeddings. The embeddings
 are saved in a parquet file. The embeddings are created
 using a networkx graph, which was populated using the json
 we retrieved from the graph database. The metadata for the
 tracks is also saved in the parquet file, named 
 'graph_embeddings_data.parquet'.
'''

import networkx as nx
from node2vec import Node2Vec
import random 
import pandas as pd
from GraphEmbedder.functions import tracks_to_networkx, tracks_to_dictionary 
import json
import os

tracks_dict = json.load(open('tracks.json', 'r'))

# Create the graph
dg = nx.DiGraph()
tracks_to_networkx(tracks_dict, dg)

# Create the Embedding Object
print('Creating Embeddings.')
node2vec = Node2Vec(dg, dimensions=32, walk_length=6, num_walks=5000, workers=6)  # CHANGE TO YOUR HEARTS CONTENT!

# Embed nodes
model = node2vec.fit(window=10, min_count=1, batch_words=4)  # Any keywords acceptable by gensim.Word2Vec can be passed, `dimensions` and `workers` are automatically passed (from the Node2Vec constructor)

# Save the Embeddings
model.wv.save_word2vec_format('Embeddings.txt')

# Create the metadata
metadata_dict = tracks_to_dictionary(tracks_dict)
metadata_df = pd.DataFrame(metadata_dict).T
metadata_df['title'] = metadata_df['title'].fillna(metadata_df['name'])
metadata_df.drop(['name', 'hasImage'], axis=1, inplace=True)

# Concat Embeddings with Metadata
embeddings = pd.read_csv('Embeddings.txt', sep=' ', skiprows=1, header=None, index_col=0)
data = pd.concat([metadata_df, embeddings], axis=1)

os.remove('Embeddings.txt')

# Save the data
data.to_parquet('graph_embeddings.parquet')
