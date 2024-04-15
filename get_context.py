'''

This script uses the lyrics of the songs
 to get the context, summary and emotional
 context of the song. It uses an API hosted
 from another script to get the data. 
 The data is then saved in a json file, named
 'tracks_contextualized.json'.
'''

import requests
import json
from tqdm import tqdm

all_tracks = json.load(open('tracks.json', 'r'))

metedata_url = f"https://w7852kszrbkrz2-4000.proxy.runpod.net/metadata"

lyrics_input = {}

for track_id in tqdm(all_tracks):
    lyrics = all_tracks[track_id]['lyrics']

    if lyrics == '':
        all_tracks[track_id]['lyrics'] = {
            'lyrics': '',
            'context': '',
            'summary': '',
            'emotional': ''
        }   
    else: 
        for attempt in range(20):  
            
            lyrics_input['text'] = lyrics
            
            headers = {
                'Content-Type': 'application/json',
                'Authorization': '...'
            }

            response = requests.post(metedata_url, json=lyrics_input, headers=headers)
            
            if 'context' in response.json():
                break
            else:
                print('Trying... Attempt:', attempt+1)
                continue

        if 'context' not in response.json():
            all_tracks[track_id]['lyrics'] = {
                'lyrics': lyrics,
                'context': '',
                'summary': '',
                'emotional': ''
            } 
        else: 
            all_tracks[track_id]['lyrics'] = {
                'lyrics': lyrics,
                'context': response.json()['context'],
                'summary': response.json()['summary'],
                'emotional': response.json()['emotional_context']
            }

json.dump(all_tracks, open('tracks_contextualized.json', 'w'), indent=4)
