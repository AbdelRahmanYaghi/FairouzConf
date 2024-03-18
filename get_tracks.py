from GraphEmbedder.functions import get_tracks_per_user
import json

users = {
    # 'Tabaza'   :'2doA06c8bZyIxBIJ5CPl7q',
    # 'Yaghi'    :'7zzLkeqvGLGC69FXG82lAx',
    # 'Omar'     :'58Pjc8vXpiDkE54OXF6CHS'
    # 'test': '3c24SVEvqpuw6hJSI4n476',
    'all': '58Pjc8vXpiDkE54OXF6CHS'
    }


# Get the tracks
print('Fetching Tracks...')
tracks_dict = get_tracks_per_user(users)

print('Fetched Tracks Successfully. Saving to JSON.')
json.dump(tracks_dict, open('tracks.json', 'w'), indent=4)
