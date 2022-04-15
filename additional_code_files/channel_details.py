from googleapiclient.discovery import build
import pandas as pd

def get_channel_stats(youtube, channel_ids):
    all_data = []

    request = youtube.channels().list(
                part='snippet,contentDetails,statistics',
                id=','.join(channel_ids))
    response = request.execute() 


    for i in range(len(response['items'])):
        data = dict(Channel_name = response['items'][i]['snippet']['title'],
                    Subscribers = response['items'][i]['statistics']['subscriberCount'],
                    Views = response['items'][i]['statistics']['viewCount'],
                    Total_videos = response['items'][i]['statistics']['videoCount'],
                    playlist_id = response['items'][i]['contentDetails']['relatedPlaylists']['uploads'])
        all_data.append(data)
    
    return all_data

def Channel_Depth_details(channel_id):
    pl_request = youtube.playlists().list(
		part='contentDetails,snippet',
		id=','.join(channel_ids),
		maxResults=50)
    pl_response = pl_request.execute()

    return len(pl_response['items'])

if __name__ == "__main__":
    channel_ids = ['UCnz-ZXXER4jOvuED5trXfEA', # techTFQ
                  ]   
    api_key = "AIzaSyAwqjWLYMnUaR4egNbKspKAxQwFYKut3E0"
    youtube = build('youtube', 'v3', developerKey=api_key)
    channel_content = get_channel_stats(youtube, channel_ids)
    channel_playlist_count = Channel_Depth_details(channel_ids)
    data = {'Playlist_count': [8]}  
    count = pd.DataFrame(data)
    print(count.ndim)
    channel_data = pd.DataFrame(channel_content)
    print(channel_data.ndim)


"""
auditDetails
brandingSettings
contentDetails
contentOwnerDetails
id
localizations
snippet
statistics
status
topicDetails
"""