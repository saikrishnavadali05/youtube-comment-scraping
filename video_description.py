from googleapiclient.discovery import build


def playlist_video_links(playlistId):

	nextPageToken = None
	
	# Creating youtube resource object
	youtube = build('youtube', 'v3',
					developerKey='AIzaSyAzbbtcETUl-ThjS3QN2wwBTBujvz3YXxY')

	while True:

		# Retrieve youtube video results
		pl_request = youtube.playlistItems().list(
			part='snippet',
			playlistId=playlistId,
			maxResults=50,
			pageToken=nextPageToken
		)
		pl_response = pl_request.execute()

		# Iterate through all response and get video description
		for item in pl_response['items']:

			description = item['snippet']['description']

			print(description)

			print("\n")

		nextPageToken = pl_response.get('nextPageToken')

		if not nextPageToken:
			break


playlist_video_links('PLavw5C92dz9FDsr995DjwCy9XNaIukb8P')
