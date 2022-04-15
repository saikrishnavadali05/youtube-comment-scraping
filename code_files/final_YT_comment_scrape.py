import pandas as pd
import json
import os
import re
import time
import requests

from youtube_comment_stats import get_channel_stats
from googleapiclient.discovery import build
from video_data_scrape import addedheader, scrape_video_title

# pandas dataframe display configuration
pd.set_option('display.max_rows', 500)
pd.set_option('display.max_columns', 500)
pd.set_option('display.width', 1000)

YOUTUBE_COMMENTS_AJAX_URL = 'https://www.youtube.com/comment_service_ajax'
YT_CFG_RE = r'ytcfg\.set\s*\(\s*({.+?})\s*\)\s*;'
YT_INITIAL_DATA_RE = r'(?:window\s*\[\s*["\']ytInitialData["\']\s*\]|ytInitialData)\s*=\s*({.+?})\s*;\s*(?:var\s+meta|</script|\n)'

# 0 : False, 1 : True 
SORT_BY_POPULAR = 0
SORT_BY_RECENT = 1

COMMENT_LIMIT = 2000

def regex_search(text, pattern, group=1, default=None):
    match = re.search(pattern, text)
    return match.group(group) if match else default

def ajax_request(session, endpoint, ytcfg, retries=5, sleep=20):
    url = 'https://www.youtube.com' + endpoint['commandMetadata']['webCommandMetadata']['apiUrl']
    
    data = {'context': ytcfg['INNERTUBE_CONTEXT'],
            'continuation': endpoint['continuationCommand']['token']}

    for _ in range(retries):
        response = session.post(url, params={'key': ytcfg['INNERTUBE_API_KEY']}, json=data)
        if response.status_code == 200:
            return response.json()
        if response.status_code in [403, 413]:
            return {}
        else:
            time.sleep(sleep)

def download_comments(video_id, sort_by=SORT_BY_RECENT, language=None, sleep=0.1):
    session = requests.Session()
    response = session.get(video_id)

    if 'uxe=' in response.request.url:
        session.cookies.set('CONSENT', 'YES+cb', domain='.youtube.com')
        response = session.get(video_id)

    html = response.text
    ytcfg = json.loads(regex_search(html, YT_CFG_RE, default=''))

    if not ytcfg:
        return # Unable to extract configuration
    if language:
        ytcfg['INNERTUBE_CONTEXT']['client']['hl'] = language

    data = json.loads(regex_search(html, YT_INITIAL_DATA_RE, default=''))

    section = next(search_dict(data, 'itemSectionRenderer'), None)
    renderer = next(search_dict(section, 'continuationItemRenderer'), None) if section else None
    if not renderer:
        # Comments disabled?
        return

    needs_sorting = sort_by != SORT_BY_POPULAR
    continuations = [renderer['continuationEndpoint']]
    while continuations:
        continuation = continuations.pop()
        response = ajax_request(session, continuation, ytcfg)

        if not response:
            break
        if list(search_dict(response, 'externalErrorMessage')):
            raise RuntimeError('Error returned from server: ' + next(search_dict(response, 'externalErrorMessage')))

        if needs_sorting:
            sort_menu = next(search_dict(response, 'sortFilterSubMenuRenderer'), {}).get('subMenuItems', [])
            if sort_by < len(sort_menu):
                continuations = [sort_menu[sort_by]['serviceEndpoint']]
                needs_sorting = False
                continue
            raise RuntimeError('Failed to set sorting')

        actions = list(search_dict(response, 'reloadContinuationItemsCommand')) + \
                  list(search_dict(response, 'appendContinuationItemsAction'))
        for action in actions:
            for item in action.get('continuationItems', []):
                if action['targetId'] == 'comments-section':
                    # Process continuations for comments and replies.
                    continuations[:0] = [ep for ep in search_dict(item, 'continuationEndpoint')]
                if action['targetId'].startswith('comment-replies-item') and 'continuationItemRenderer' in item:
                    # Process the 'Show more replies' button
                    continuations.append(next(search_dict(item, 'buttonRenderer'))['command'])

        for comment in reversed(list(search_dict(response, 'commentRenderer'))):
            video_data_dict = {
                'cid': comment['commentId'],
                'text': ''.join([c['text'] for c in comment['contentText'].get('runs', [])]),
                'time': comment['publishedTimeText']['runs'][0]['text'],
                'author': comment.get('authorText', {}).get('simpleText', ''),
                'channel': comment['authorEndpoint']['browseEndpoint'].get('browseId', ''),
                'votes': comment.get('voteCount', {}).get('simpleText', '0'),
                'photo': comment['authorThumbnail']['thumbnails'][-1]['url'],
                'heart': next(search_dict(comment, 'isHearted'), False)
                }

            yield video_data_dict

        time.sleep(sleep)

def search_dict(partial, search_key):
    stack = [partial]
    while stack:
        current_item = stack.pop()
        if isinstance(current_item, dict):
            for key, value in current_item.items():
                if key == search_key:
                    yield value
                else:
                    stack.append(value)
        elif isinstance(current_item, list):
            for value in current_item:
                stack.append(value)

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

    start_time = time.time()

    channel_ids = ['UCnz-ZXXER4jOvuED5trXfEA']
    api_key = "AIzaSyAzbbtcETUl-ThjS3QN2wwBTBujvz3YXxY"
    youtube_access = build('youtube', 'v3', developerKey=api_key)
    channel_content = get_channel_stats(youtube_access, channel_ids)

    print("---------------------")
    print(f"channel_content : {channel_content}")
    print("---------------------")

    channel_data = pd.DataFrame(channel_content)
    print("---------------------")
    print(channel_data)
    print("---------------------")

    ids_of_videos = get_video_ids(youtube_access, channel_data)
    print("---------------------")
    print(ids_of_videos)
    print("---------------------")
    
    complete_video_ids = []
    # video_titles = []

    for video_id in ids_of_videos:
        complete_video_path = "https://www.youtube.com/watch?v=" + video_id
        print(complete_video_path)
        complete_video_ids.append(complete_video_path)
    
    if not os.path.exists(r"youtube-comment-scraping/temporary_code_files"):
        print("temporary_code_files folder doesnot exist. Creating now")
        os.mkdir("temporary_code_files")

    temporary_title_file = r"temporary_code_files/temp_titles.csv"
    headerList = ['name_of_video']
    addedheader(headerList, temporary_title_file)
    video_titles = scrape_video_title(ids_of_videos, temporary_title_file)
    print(video_titles)

    data_tuples = list(zip(complete_video_ids, video_titles))
    df = pd.DataFrame(data_tuples, columns=['complete_video_IDs', 'video_titles'])
    df.to_csv('temporary_code_files/channel_video_ids.csv', index=False)

    video_id_df = pd.read_csv('temporary_code_files/channel_video_ids.csv')
    complete_video_ids = list(video_id_df['complete_video_IDs'].values)
    video_titles = list(video_id_df['video_titles'].values)

    if not os.path.exists(r"youtube-comment-scraping/outputs"):
        print("Outputs folder doesnot exist. Creating now")
        os.mkdir("outputs")

    video_count = 0
    for video_title, video_id in zip(video_titles, complete_video_ids):
        df_comment = pd.DataFrame()

        try:
            limit = COMMENT_LIMIT
            print("#############################################################")
            print(f"video_count : {video_count}")
            print('Extracting Youtube comments for the video with ID:', video_id)
            
            for comment_idx, comment in enumerate(download_comments(video_id), start=0):
                df_comment = df_comment.append(comment, ignore_index=True)
                comment_json = json.dumps(comment, ensure_ascii=False)
                comment_json_dict: json.loads(comment_json)

                if limit and comment_idx >= limit:
                    break

            FILE_NAME = f'outputs/ytb_comments{video_title}.csv'
            if not os.path.isfile(FILE_NAME):
                df_comment.to_csv(FILE_NAME, encoding='utf-8', index=False)
            else:
                df_comment.to_csv(FILE_NAME, mode='a', encoding='utf-8', index=False, header=False)

            print("Finished extracting comments for the video. Moving on to next video")
            print(f"Comments and other data can be found at : {FILE_NAME} file")
            print("#############################################################")
        except Exception as e:
            print('Error:', str(e))
            print(f"Failed at this video : {video_title}")
            print("continuing with the next video from the same channel")                       

        video_count += 1

    end_time = time.time()
    time_difference = end_time - start_time
    print('\n Time taken to execute : {:.2f} seconds'.format(time_difference))
