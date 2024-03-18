import requests
import json
from tqdm import tqdm

all_tracks = json.load(open('tracks.json', 'r'))

metedata_url = f"https://b4samtzdgv8ja8-4000.proxy.runpod.net/metadata"

lyrics_input = {}

for user in all_tracks:
    for track_id in tqdm(all_tracks[user]['tracks']):
        lyrics = all_tracks[user]['tracks'][track_id]['lyrics']

        if lyrics == '':
            all_tracks[user]['tracks'][track_id]['lyrics'] = {
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
                    'Authorization': 'Bearer 543c7086-c880-45de-8bce-6c9c906293bb'
                }
                response = requests.post(metedata_url, json=lyrics_input, headers=headers)
                
                if 'context' in response.json():
                    break
                else:
                    print('Trying... Attempt:', attempt+1)
                    continue

            if 'context' not in response.json():
                all_tracks[user]['tracks'][track_id]['lyrics'] = {
                    'lyrics': lyrics,
                    'context': '',
                    'summary': '',
                    'emotional': ''
                } 
            else: 
                all_tracks[user]['tracks'][track_id]['lyrics'] = {
                    'lyrics': lyrics,
                    'context': response.json()['context'],
                    'summary': response.json()['summary'],
                    'emotional': response.json()['emotional_context']
                }

json.dump(all_tracks, open('tracks_contextualized.json', 'w'), indent=4)
