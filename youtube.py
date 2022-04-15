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


# channel_statistics = get_channel_stats(youtube, channel_ids)

def get_video_ids(youtube, playlist_id):
    playlist_id = channel_data.loc[channel_data['Channel_name']=='techTFQ', 'playlist_id'].iloc[0]
    request = youtube.playlistItems().list(
                part='contentDetails',
                playlistId = playlist_id,
                maxResults = 50)
    response = request.execute()
    
    video_ids = []
    
    for i in range(len(response['items'])):
        video_ids.append(response['items'][i]['contentDetails']['videoId'])
        
    next_page_token = response.get('nextPageToken')
    more_pages = True
    
    while more_pages:
        if next_page_token is None:
            more_pages = False
        else:
            request = youtube.playlistItems().list(
                        part='contentDetails',
                        playlistId = playlist_id,
                        maxResults = 50,
                        pageToken = next_page_token)
            response = request.execute()
    
            for i in range(len(response['items'])):
                video_ids.append(response['items'][i]['contentDetails']['videoId'])
            
            next_page_token = response.get('nextPageToken')
        
    return video_ids

# video_ids = get_video_ids(youtube, playlist_id)

# print(video_ids)

# box = [['Name', 'Comment', 'Time', 'Likes', 'Reply Count']]


def scrape_comments_with_replies(video_ids):
    box = [['Name', 'Comment', 'Time', 'Likes', 'Reply Count']]
    for i in range(0, len(video_ids), 50):
        data = youtube.commentThreads().list(part='snippet', videoId=video_ids[i], maxResults='100', textFormat="plainText").execute()
    for i in data["items"]:
        name = i["snippet"]['topLevelComment']["snippet"]["authorDisplayName"]
        comment = i["snippet"]['topLevelComment']["snippet"]["textDisplay"]
        published_at = i["snippet"]['topLevelComment']["snippet"]['publishedAt']
        likes = i["snippet"]['topLevelComment']["snippet"]['likeCount']
        replies = i["snippet"]['totalReplyCount']
        box.append([name, comment, published_at, likes, replies])
        totalReplyCount = i["snippet"]['totalReplyCount']
        if totalReplyCount > 0:
            parent = i["snippet"]['topLevelComment']["id"]
            data2 = youtube.comments().list(part='snippet', maxResults='100', parentId=parent,
                                            textFormat="plainText").execute()
            for i in data2["items"]:
                name = i["snippet"]["authorDisplayName"]
                comment = i["snippet"]["textDisplay"]
                published_at = i["snippet"]['publishedAt']
                likes = i["snippet"]['likeCount']
                replies = ""
                box.append([name, comment, published_at, likes, replies])
    while ("nextPageToken" in data):
        for i in range(0, len(video_ids), 50):
            data = youtube.commentThreads().list(part='snippet', videoId=video_ids[i], pageToken=data["nextPageToken"],
                                             maxResults='100', textFormat="plainText").execute()
        for i in data["items"]:
            name = i["snippet"]['topLevelComment']["snippet"]["authorDisplayName"]
            comment = i["snippet"]['topLevelComment']["snippet"]["textDisplay"]
            published_at = i["snippet"]['topLevelComment']["snippet"]['publishedAt']
            likes = i["snippet"]['topLevelComment']["snippet"]['likeCount']
            replies = i["snippet"]['totalReplyCount']
            box.append([name, comment, published_at, likes, replies])
            totalReplyCount = i["snippet"]['totalReplyCount']
            if totalReplyCount > 0:
                parent = i["snippet"]['topLevelComment']["id"]
                data2 = youtube.comments().list(part='snippet', maxResults='100', parentId=parent,
                                                textFormat="plainText").execute()
                for i in data2["items"]:
                    name = i["snippet"]["authorDisplayName"]
                    comment = i["snippet"]["textDisplay"]
                    published_at = i["snippet"]['publishedAt']
                    likes = i["snippet"]['likeCount']
                    replies = ''
                    box.append([name, comment, published_at, likes, replies])
    df = pd.DataFrame({'Name': [i[0] for i in box], 'Comment': [i[1] for i in box], 'Time': [i[2] for i in box],
                       'Likes': [i[3] for i in box], 'Reply Count': [i[4] for i in box]})
    df.to_json('file1.json', orient = 'split', compression = 'infer', index=False)
    return "Successful! Check the CSV file that you have just created."

if __name__ == "__main__":
    channel_ids = ['UCnz-ZXXER4jOvuED5trXfEA', # techTFQ
                  ]   
    api_key = "AIzaSyAzbbtcETUl-ThjS3QN2wwBTBujvz3YXxY"
    youtube = build('youtube', 'v3', developerKey=api_key)
    channel_content = get_channel_stats(youtube, channel_ids)
    channel_data = pd.DataFrame(channel_content)
    print(channel_data)
    ids_of_videos = get_video_ids(youtube, channel_data)
    print(type(ids_of_videos[0]))
    #comments = scrape_comments_with_replies(ids_of_videos)

