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
            try:
                lyrics_input['text'] = lyrics
                headers = {
                    'Content-Type': 'application/json',
                    'Authorization': 'Bearer 543c7086-c880-45de-8bce-6c9c906293bb'
                }
                response = requests.post(metedata_url, json=lyrics_input, headers=headers)
                response.json()['context']
            except:
                try:
                    print('Failed Once, trying again...')
                    response = requests.post(metedata_url, json=lyrics_input, headers=headers)
                    response.json()['context']
                except:
                    try:
                        print('Failed Twice, trying again...')
                        response = requests.post(metedata_url, json=lyrics_input, headers=headers)
                        response.json()['context']
                    except:
                        try:
                            print('Failed Thrice, trying again...')
                            response = requests.post(metedata_url, json=lyrics_input, headers=headers)
                            response.json()['context']
                        except Exception as e:
                            print('Failed Four Times, skipping...')
                            print(f'User: {user}')
                            print(f'Track: {track_id}')
                            print(f'Error Code: {e}')
                            continue
                                
                        

            all_tracks[user]['tracks'][track_id]['lyrics'] = {
                'lyrics': lyrics,
                'context': response.json()['context'],
                'summary': response.json()['summary'],
                'emotional': response.json()['emotional_context']
            }

json.dump(all_tracks, open('tracks_contextualized.json', 'w'), indent=4)

