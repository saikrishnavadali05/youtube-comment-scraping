# youtube-comment-scraping
> Scrape all the comments from all the videos of a youtube channel

## Folder Hierarchy
1. **code_files** 
> Complete working code (all the files that being used for the entire application).
2. **outputs**
> The complete data extracted for all the videos belonging to the particular channel
3. **temporary_code_files**
> All the temporary files that get generated during code execution.
4. **additional_code_files**
> All the additional features that can be used and implemented on the application if the need arises.

### Master Code Reference (works for a single video execution):
1. https://github.com/ahmedshahriar/youtube-comment-scraper/blob/main/Youtube_comment_parser.ipynb

### Steps to extract channel-id:
1. The ID of the youtube video channel for which comments have to be extracted has to be found out first.
2. To find out the channel ID, please follow the image shown below.

![how to get the channel ID of youtube videos?](https://github.com/saikrishnavadali05/youtube-comment-scraping/blob/master/Screenshot%20(219).png)

## Commands to run the entire application : 
1. Install all the dependencies
> ```pip install -r requirements.txt```
2. Run the Framework
> ```python ./code_files/final_YT_comment_scrape.py```
3. Paste the channel ID in the channel_id's list present in the ```final_YT_comment_scrape.py```
4. To get the channel ID, follow the image shown above.

