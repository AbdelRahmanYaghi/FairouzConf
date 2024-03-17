from GraphEmbedder.classes import SpotifyAPIUser
import discogs_client
import hashlib
import string
import deezer as deezer_client
import json
from tqdm import tqdm
from neo4j import GraphDatabase
import networkx as nx
import pandas as pd
import re
import os
from dotenv import load_dotenv
from node2vec import Node2Vec
from fuzzywuzzy import fuzz
import unicodedata
import urllib.parse
import requests
from bs4 import BeautifulSoup
from rdflib import Graph, Literal, Namespace, RDF, RDFS, XSD

load_dotenv()

SPOTIFY_CLIENT_ID = os.getenv('SPOTIFY_CLIENT_ID')
SPOTIFY_SECRET_ID = os.getenv('SPOTIFY_SECRET_ID')
DISCOGS_USER_TOKEN = os.getenv('DISCOGS_USER_TOKEN')

idify = lambda my_string: str(hashlib.md5(my_string.encode()).hexdigest())
sanitize = lambda string: re.match(r'^\(?[\w\'\"\. ¡!’]+\)?', string)[0].strip()

def get_tracks(spotify_playlist_id):
    '''
    This function gets the tracks from a spotify playlist 
     - and returns a dictionary with the tracks and their information.
    '''

    spotify_api = SpotifyAPIUser(SPOTIFY_CLIENT_ID, SPOTIFY_SECRET_ID)
    user_songs = spotify_api.get_tracks_from_playlist(spotify_playlist_id)

    discogs = discogs_client.Client('Fairouz', user_token=DISCOGS_USER_TOKEN)
    deezer = deezer_client.Client()

    tracks = {}
    songs_not_found = []

    for song_name, artist_name in tqdm(user_songs):
        print(song_name, artist_name)
        song_name = sanitize(song_name)
        results = discogs.search(song_name, artist=artist_name, type='master')
        results = results.sort(key=lambda x: x.data.community.have, order='desc').filter(format='Album')
        result = 'id'+idify(f'{song_name}{artist_name}')
        lyrics, genius_id = match_results(song_name, artist_name)

        try:
            song = deezer.search(artist=artist_name, track=song_name)
            tracks[result] = {
                'deezer_id': song[0].id,
                'discogs_id': '',
                'track_name': song[0].title_short ,
                'artist_name': song[0].artist.name,
                'album_name': song[0].album.title,
                'genres': [i.name for i in song[0].album.genres],
                'images': song[0].album.cover,
                'lyrics': lyrics,
                'preview_url': song[0].preview
            }
        except:
            try: 
                genres = results[0].genres
                if results[0].styles is not None:
                    genres.extend(results[0].styles)
                    
                for track in results[0].tracklist:
                    if fuzz.ratio(song_name, track.title) >= 80 :
                        discogs_track_name = track.title
                        discogs_artist_name = track.artists[0].name
                    else:
                        raise Exception(f"Track name {song_name} not found in Discogs. Found {track.title} instead.")

                tracks[result] = {
                    'deezer_id': '',
                    'discogs_id': results[0].id,
                    'track_name': discogs_track_name,
                    'artist_name': discogs_artist_name,
                    'album_name': results[0].title.replace(discogs_artist_name, "").replace(" - ", "").replace("(", "").replace(")", "").replace("  ", " ").strip(),
                    'genres': genres,
                    'images': results[0].images[0]['uri'],
                    'lyrics': lyrics
                }
            except Exception as e:
                songs_not_found.append({'Song Name': song_name, 'Artist': artist_name, 'Error': str(e)})

    print(f"Found tracks: {len(tracks)}\nNot found tracks: {len(songs_not_found)}")
    print(f"Perc of found tracks: {len(tracks) / (len(tracks) + len(songs_not_found)) * 100}%")
    return tracks, songs_not_found

def get_tracks_per_user(users):
    '''
    This function gets the tracks from a dict
     - of users and returns a dictionary with 
     - the tracks and their information.
    '''
    tracks_users = {}
    for user in users:
        print(f'Getting tracks for {user}...')
        spotify_playlist_id = users[user]
        tracks, songs_not_found = get_tracks(spotify_playlist_id)
        tracks_users[user] = {
            'tracks': tracks,
            'songs_not_found': songs_not_found
        }
    return tracks_users

def tracks_to_cypher(tracks_dict):
    '''
    This function takes a dictionary of tracks of each user and 
     - returns a string with the cypher query to create the graph
     - in Neo4j.
    '''
    track_set = set()
    artist_set = set()
    album_set = set()
    genre_set = set()

    cqlCreate = """

    CREATE

    """
    for user in tracks_dict:
        tracks = tracks_dict[user]['tracks']
        for track_id in tracks:  
            #################
            ### Add Track ###
            #################
            track = tracks[track_id]
            
            track_title = track['song_name']
            artist_name = track['artist_name']
            album_name = track['album_name']
            album_image = track['images']

            if track_id not in track_set:
                cqlCreate += f'({track_id}:track {{title:"{track_title}"}}),\n'
            
            artist_id = 'id' + idify('artist' +track['artist_name'])
            album_id = 'id' + idify('album' +track['album_name'])
            genres_id  = {}

            for genre in track['genres']:
                if isinstance(genre, str):
                    genre_id = 'id' + idify('genre' + genre)
                    genres_id[genre_id] = genre
                else:
                    genre_id = 'id' + idify('genre' + genre.name)
                    genres_id[genre_id] = genre.name
            #  = {'id' + idify('genre' + genre.name): genre  for genre in track['genres']}

            ##################
            ### Add Artist ###
            ##################

            if artist_id not in artist_set:
                cqlCreate += f'({artist_id}:artist {{name:"{artist_name}"}}),\n'

            #################
            ### Add Album ###
            #################
            if album_id not in album_set and album_name != '':
                cqlCreate += f'({album_id}:album {{title:"{album_name}", hasImage: "{album_image}"}}),\n'
                cqlCreate += f'({album_id})-[:BY_ARTIST]->({artist_id}),\n'

            ##################
            ### Add Genres ###
            ##################

            for genre_id in genres_id:
                if genre_id not in genre_set:
                    genre_name = genres_id[genre_id]
                    cqlCreate += f'({genre_id}:genre {{name:"{genre_name}"}}),\n'
                    genre_set.add(genre_id)


            if track_id not in track_set:
                for genre_id in genres_id:
                    cqlCreate += f'({track_id})-[:HAS_GENRE]->({genre_id}),\n'
                cqlCreate += f'({track_id})-[:BY_ARTIST]->({artist_id}),\n'
                if album_name != '':
                    cqlCreate += f'({track_id})-[:PART_OF_ALBUM]->({album_id}),\n'
            
            # cqlCreate += f'({track_id})-[:LIKED_BY]->({user_id}),\n'

            track_set.add(track_id)
            artist_set.add(artist_id)
            album_set.add(album_id)

            cqlCreate += '\n'

    if cqlCreate[-3] == ',':
        cqlCreate = cqlCreate[:-3]

    return cqlCreate

def tracks_to_networkx(tracks_dict, graph):
    track_set = set()
    artist_set = set()
    album_set = set()
    genre_set = set()

    for user in tracks_dict:
        tracks = tracks_dict[user]['tracks']
        for track_id in tracks:  

            #################
            ### Add Track ###
            #################
            track = tracks[track_id]
            
            track_title = track['song_name']
            artist_name = track['artist_name']
            album_name = track['album_name']
            album_image = track['images']

            if track_id not in track_set:
                graph.add_node(track_id, title=track_title, type='track')
            
            artist_id = 'id' + idify('artist' +track['artist_name'])
            album_id = 'id' + idify('album' +track['album_name'])
            genres_id  = {}

            for genre in track['genres']:
                if isinstance(genre, str):
                    genre_id = 'id' + idify('genre' + genre)
                    genres_id[genre_id] = genre
                else:
                    genre_id = 'id' + idify('genre' + genre.name)
                    genres_id[genre_id] = genre.name

            ##################
            ### Add Artist ###
            ##################

            if artist_id not in artist_set:
                graph.add_node(artist_id, name=artist_name, type='artist')

            #################
            ### Add Album ###
            #################
            if album_id not in album_set and album_name != '':
                graph.add_node(album_id, title=album_name, hasImage=album_image, type='album')
                graph.add_edge(album_id, artist_id, type='BY_ARTIST')

            ##################
            ### Add Genres ###
            ##################

            for genre_id in genres_id:
                if genre_id not in genre_set:
                    genre_name = genres_id[genre_id]
                    graph.add_node(genre_id, name=genre_name, type='genre')
                    genre_set.add(genre_id)


            if track_id not in track_set:
                for genre_id in genres_id:
                    graph.add_edge(track_id, genre_id, type='HAS_GENRE')
                graph.add_edge(track_id, artist_id, type='BY_ARTIST')
                if album_name != '':
                    graph.add_edge(track_id, album_id, type='PART_OF_ALBUM')
            
            # graph.add_edge(track_id, user_id, type='LIKED_BY')

            track_set.add(track_id)
            artist_set.add(artist_id)
            album_set.add(album_id)


def tracks_to_graphdb(tracks_dict):

    ns = Namespace("http://psut.edu.jo/fAIrouz/")

    g = Graph()
    g.bind("ex", ns)

    track_set = set()
    artist_set = set()
    album_set = set()
    genre_set = set()

    for user in tracks_dict:
        tracks = tracks_dict[user]['tracks']

        for track_id in tracks:

            #################
            ### Add Track ###
            #################
            track = tracks[track_id]

            track_title = track['track_name']
            track_lyrics = track['lyrics']
            track_preview = track['preview_url']
            artist_name = track['artist_name']
            album_name = track['album_name']
            album_image = track['images']

            if track_id not in track_set:
                g.add((ns[str(track_id)], RDF.type, ns.track))
                g.add((ns[str(track_id)], RDFS.label, Literal(str(track_title), datatype = XSD.string)))
                g.add((ns[str(track_id)], ns.title, Literal(str(track_title), datatype = XSD.string)))
                g.add((ns[str(track_id)], ns.lyrics, Literal(str(track_lyrics), datatype = XSD.string)))
                g.add((ns[str(track_id)], ns.preview_url, Literal(str(track_preview), datatype = XSD.string)))

            
            artist_id = 'id' + idify('artist' +track['artist_name'])
            album_id = 'id' + idify('album' +track['album_name'])
            genres_id  = {}

            for genre in track['genres']:
                if isinstance(genre, str):
                    genre_id = 'id' + idify('genre' + genre)
                    genres_id[genre_id] = genre
                else:
                    genre_id = 'id' + idify('genre' + genre.name)
                    genres_id[genre_id] = genre.name

            ##################
            ### Add Artist ###
            ##################
            if artist_id not in artist_set:
                g.add((ns[str(artist_id)], RDF.type, ns.artist))
                g.add((ns[str(artist_id)], RDFS.label, Literal(str(artist_name), datatype = XSD.string)))
                g.add((ns[str(artist_id)], ns.name, Literal(str(artist_name), datatype = XSD.string)))


            #################
            ### Add Album ###
            #################
            if album_id not in album_set and album_name != '':
                    
                g.add((ns[str(album_id)], RDF.type, ns.album))
                g.add((ns[str(album_id)], ns.title, Literal(str(album_name), datatype = XSD.string)))
                g.add((ns[str(album_id)], RDFS.label, Literal(str(album_name), datatype = XSD.string)))
                g.add((ns[str(album_id)], ns.hasImage, Literal(str(album_image), datatype = XSD.string)))
                g.add((ns[str(album_id)], ns.byArtist, ns[str(artist_id)]))

            ##################
            ### Add Genres ###
            ##################

            for genre_id in genres_id:
                if genre_id not in genre_set:
                    genre_name = genres_id[genre_id]
                    
                    g.add((ns[str(genre_id)], RDF.type, ns.genre))
                    g.add((ns[str(genre_id)], ns.name, Literal(str(genre_name), datatype = XSD.string)))
                    g.add((ns[str(genre_id)], RDFS.label, Literal(str(genre_name), datatype = XSD.string)))

                    genre_set.add(genre_id)

            if track_id not in track_set:
                for genre_id in genres_id:
                    g.add((ns[str(track_id)], ns.hasGenre, ns[str(genre_id)]))     

                g.add((ns[str(track_id)], ns.byArtist, ns[str(artist_id)]))
                if album_name != '':
                    g.add((ns[str(track_id)], ns.partOfAlbum, ns[str(album_id)]))

            track_set.add(track_id)
            artist_set.add(artist_id)
            album_set.add(album_id)

        turtle = g.serialize(format='turtle')

        with open('fairouz_abox.ttl', 'w', encoding='utf8') as f:
            f.write(turtle)


def get_lyrics(url):
    page = requests.get(url)
    html = BeautifulSoup(page.text, "html.parser")

    lyrics = html.find_all("div", {"class": "Lyrics__Container-sc-1ynbvzw-1 kUgSbL"})

    all_lyrics = []

    for lyric in lyrics:
        for br_tag in lyric.find_all("br"):
            br_tag.insert_after("\n")

        lyric = lyric.get_text()

        all_lyrics.append(lyric)

    return "\n".join(all_lyrics)

normalize_respose = lambda response: unicodedata.normalize("NFKD", response)

def query_genius(song_name, artist_name=""):
    search_query = f"{song_name} {artist_name}"
    encoded_search_query = urllib.parse.quote(search_query)
    genius_url = f"https://api.genius.com/search?q={encoded_search_query}"
    headers = {
        "Authorization": "Bearer sbuQDc9_p5rm5aGbUuncdJ6zQLNV25HMXB-K4DDLrPQsx7cRyqH4OZIaA1KW-rhW"
    }
    response = requests.get(genius_url, headers=headers).json()

    all_items_list = []

    for hit in response["response"]["hits"]:

        normalized_response = {   
            "title": normalize_respose(hit["result"]["title"]),
            "title_with_featured": normalize_respose(hit["result"]["title_with_featured"]),
            "full_title": normalize_respose(hit["result"]["full_title"]),
            "artist_name": normalize_respose(hit["result"]["artist_names"]),
            "urls": hit["result"]["url"],
            "genius_id": hit["result"]["id"]
        }

        all_items_list.append(normalized_response)

    return all_items_list

def match_results(song_name, artist_name, threshold=60):

    res = []  
    song_name = sanitize(song_name)
    results = query_genius(song_name, artist_name)

    for result in results:
        
        title, title_with_featured, full_title, artist_name_, url, id_ = result.values()

        title_match = fuzz.partial_ratio(song_name, title)
        title_with_featured_match = fuzz.partial_ratio(song_name, title_with_featured)
        full_title_match = fuzz.partial_ratio(song_name, full_title)
        artist_name_match = fuzz.partial_ratio(artist_name, artist_name_)
        
        sum_match = (title_match + title_with_featured_match +
                     full_title_match + artist_name_match ) / 4

        res.append(result | {"match": sum_match})


    res = sorted(res, key=lambda x: x["match"], reverse=True)
    if res:
        if res[0]["match"] < threshold:
            return ('', '')

        lyrics = get_lyrics(res[0]["urls"])
        genius_id = res[0]["genius_id"]

        if lyrics != "":
            return lyrics, genius_id
    
    
    return ('', '')
        
    
