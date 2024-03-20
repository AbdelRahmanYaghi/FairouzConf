'''
This script is used to get the tracks from
 a user and save them into a ttl file, named
 'fairouz_abox.ttl'.
'''

from GraphEmbedder.functions import get_tracks_per_user, tracks_to_ttl
import json

users = {
    'all': '58Pjc8vXpiDkE54OXF6CHS'
    }

# Get the tracks
print('Fetching Tracks...')
tracks_dict = get_tracks_per_user(users)

# Since we don't currently own a server, we save tracks into a ttl file, and
#   then we can upload it locally.
tracks_to_ttl(tracks_dict)