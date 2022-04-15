import pandas as pd
import json
import os
import sys
import re
import time

import requests

# pandas dataframe display configuration
pd.set_option('display.max_rows', 500)
pd.set_option('display.max_columns', 500)
pd.set_option('display.width', 1000)

YOUTUBE_COMMENTS_AJAX_URL = 'https://www.youtube.com/comment_service_ajax'

# csv file name
FILE_NAME = 'ytb_comments.csv'
YT_CFG_RE = r'ytcfg\.set\s*\(\s*({.+?})\s*\)\s*;'
YT_INITIAL_DATA_RE = r'(?:window\s*\[\s*["\']ytInitialData["\']\s*\]|ytInitialData)\s*=\s*({.+?})\s*;\s*(?:var\s+meta|</script|\n)'
# set parameters
# filter comments by popularity or recent, 0:False, 1:True
SORT_BY_POPULAR = 0
# default recent
SORT_BY_RECENT = 1
# set comment limit
COMMENT_LIMIT = 100



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


def download_comments(YOUTUBE_VIDEO_URL, sort_by=SORT_BY_RECENT, language=None, sleep=0.1):
    session = requests.Session()
    response = session.get(YOUTUBE_VIDEO_URL)

    if 'uxe=' in response.request.url:
        session.cookies.set('CONSENT', 'YES+cb', domain='.youtube.com')
        response = session.get(YOUTUBE_VIDEO_URL)

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
            yield {'cid': comment['commentId'],
                   'text': ''.join([c['text'] for c in comment['contentText'].get('runs', [])]),
                   'time': comment['publishedTimeText']['runs'][0]['text'],
                   'author': comment.get('authorText', {}).get('simpleText', ''),
                   'channel': comment['authorEndpoint']['browseEndpoint'].get('browseId', ''),
                   'votes': comment.get('voteCount', {}).get('simpleText', '0'),
                   'photo': comment['authorThumbnail']['thumbnails'][-1]['url'],
                   'heart': next(search_dict(comment, 'isHearted'), False)}

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


if __name__ == "__main__":
    ytb_video_list = ['https://www.youtube.com/watch?v=-DiOp9vAEuM']
    channel_path = ""

    for video_link in ytb_video_list:
        url = video_link
        df_comment = pd.DataFrame()
        try:
            youtube_url = url
            limit = COMMENT_LIMIT

            print('Downloading Youtube comments for video:', youtube_url)

            count = 0

            start_time = time.time()

            for comment in download_comments(youtube_url):

                df_comment = df_comment.append(comment, ignore_index=True)

                # comments overview
                comment_json = json.dumps(comment, ensure_ascii=False)
                print(comment_json)

                count += 1

                if limit and count >= limit:
                    break

            print("DataFrame Shape: ",df_comment.shape,"\nComment DataFrame: ", df_comment)

            if not os.path.isfile(FILE_NAME):
                df_comment.to_csv(FILE_NAME, encoding='utf-8', index=False)
            else:  # else it exists so append without writing the header
                df_comment.to_csv(FILE_NAME, mode='a', encoding='utf-8', index=False, header=False)

            print('\n[{:.2f} seconds] Done!'.format(time.time() - start_time))

        except Exception as e:
            print('Error:', str(e))
            sys.exit(1)
