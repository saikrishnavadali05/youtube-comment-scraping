import urllib.request
import json
import urllib
import pandas as pd


def addedheader(headerlist, temporary_title_file):
    """Used to add header to the CSV files"""
    header_data = pd.DataFrame(columns=headerlist)
    header_data.to_csv(temporary_title_file, mode='a', index=False)

def scrape_video_title(VideoIDs, temporary_title_file):
    
    for VideoID in VideoIDs:
        params = {"format": "json", "url": f"https://www.youtube.com/watch?v={VideoID}"}
        url = "https://www.youtube.com/oembed"
        query_string = urllib.parse.urlencode(params)
        url = url + "?" + query_string
        video_titles = []

        try:
            with urllib.request.urlopen(url) as response:
                response_text = response.read()
                data = json.loads(response_text.decode())
                video_titles.append(data['title'])
                df = pd.DataFrame(video_titles)
                df.to_csv(temporary_title_file, mode='a',index=False, header=False)

        except Exception as e:
            print("Video couldnot be accessed.")
            video_titles.append("unaccessible video. The creator has not permitted to access his creation")
            df = pd.DataFrame(video_titles)
            df.to_csv(temporary_title_file, mode='a',index=False, header=False)
            continue     

    df = pd.read_csv(temporary_title_file)
    listed = df.values.tolist()
    only_titles = []

    for i in range(0, len(listed)):
        no_space_string = listed[i][0].replace(" ", "_")
        split_string = no_space_string.split("|", 1)
        substring = split_string[0]
        seperated_string = substring.split("_")
        merged_string = "" + seperated_string[0] + "" + seperated_string[1] + "" + seperated_string[2] + "" + seperated_string[3]
        only_titles.append(merged_string)

    print(">>>>>>>>>>>>>>>>>>>>>>>>>>>>")    
    print("only_titles : ", only_titles)
    print(">>>>>>>>>>>>>>>>>>>>>>>>>>>>")

    return only_titles

if __name__ == "_main_":
    print("sairam")
    temporary_title_file = r"temporary_code_files/temp_titles.csv"
    headerList = ['name_of_video']
    addedheader(headerList, temporary_title_file)
    VideoIDs = ['-DiOp9vAEuM', 'O1o9m9T1c3k', '7hZYh9qXxe4', 'aE623ff7zkM', 'eXJGjbDo5KY', 'O52sweYbCyI', 'cLSxasHg9WY']  
    video_titles = scrape_video_title(VideoIDs, temporary_title_file)
    print("jairam")