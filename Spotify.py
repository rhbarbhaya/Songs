# -*- coding: utf-8 -*-
"""
Created on Tue Sep 15 20:43:36 2020

@author: Rushabh Barbhaya
"""
import requests
import datetime
from urllib.parse import urlencode
import base64
from collections import defaultdict
import pandas as pd
import numpy as np
import os
import re
from time import sleep
from random import randint

class SpotifyAPI(object):
	"""SpotifyAPI is a simple, homegrown API to get all your public playlists to a excel file.
	It just needs your <Spotify Link>. There are 2 primary methods you can call.

	1. <get_playlist_tracks>: If you're looking for a specific playlist, not all, you can use this to get the specific playlist
	2. <everything>: It gets all your public playlists. No sign-in needed.

	Args:
		str ([user_link]): Your spotify link

	Raises:
		None that I know off

	Returns:
		[Excel_file]: It returns an Excel file with:
		    1. Track Name: Well, track name
			2. Track ID: Unique Track ID which Spotify provides to that track
			3. Artist Name: Again, artist(s) name(s)
			4. Artist ID: Unique artist(s) ID which Spotify provides to that artist(s)
			5. Album Name, ID and Art: Dude, same as above, it's not rocket science
	"""
	user_id = ""
	access_token = None
	access_token_expires = datetime.datetime.now()
	client_id = os.environ.get('SPOTIFY_CLIENT_ID')
	client_secret = os.environ.get('SPOTIFY_CLIENT_SECRET')
	access_token_did_expire = True
	token_url = "https://accounts.spotify.com/api/token"
	data = None
    
	def __init__(self, user_id, *args, **kwargs):
		super().__init__(*args, **kwargs)
		self.user_id = user_id
		client_id = os.environ.get('SPOTIFY_CLIENT_ID')
		client_secret = os.environ.get('SPOTIFY_CLIENT_SECRET')
		if self.user_id.find("/user/") != -1:
			self.user_id = re.search(r"(?<=user/)\w+", user_id).group(0)
		else:
			self.user_id = user_id
		
	def get_client_credentials(self):
		"""
		Returns a base64 encoded string
		"""
		client_id = self.client_id
		client_secret = self.client_secret
		if client_secret == None or client_id == None:
		    raise Exception("You must set client_id and client_secret")
		client_creds = f"{client_id}:{client_secret}"
		client_creds_b64 = base64.b64encode(client_creds.encode())
		return client_creds_b64.decode()

	def get_token_headers(self):
		client_creds_b64 = self.get_client_credentials()
		return {"Authorization": f"Basic {client_creds_b64}"}

	def get_token_data(self):
		return {"grant_type": "client_credentials"} 

	def perform_auth(self):
		token_url = self.token_url
		token_data = self.get_token_data()
		token_headers = self.get_token_headers()
		r = requests.post(token_url, data=token_data, headers=token_headers)
		if r.status_code not in range(200, 299):
			print(r.message)
			return False
		data = r.json()
		now = datetime.datetime.now()
		access_token = data['access_token']
		expires_in = data['expires_in'] # seconds
		expires = now + datetime.timedelta(seconds=expires_in)
		self.access_token = access_token
		self.access_token_expires = expires
		self.access_token_did_expire = expires < now
		
		return True

	def headers(self):
		if self.perform_auth():
			pass
		else:
			self.perform_auth()
		access_token = self.access_token
		return {
		'Accept': 'application/json',
		'Content-Type': 'application/json',
		'Authorization': f'Bearer {access_token}',
		}

	def params(self):
		return {('fields','total,next')}

	def user_info(self):
		headers = self.headers()
		user_id = self.user_id
		r = requests.get(f"https://api.spotify.com/v1/users/{user_id}", headers=headers)
		if r.status_code not in range(200, 299):
			data = r.json()
			print(data["error"]["message"])
			return 
		else:
			user_info = r.json()
			print("\n--------------------------")
			print("Hello: ", user_info["display_name"], "\n--------------------------\n")
			return user_info

	def get_user_playlists(self):
		headers = self.headers()
		user_id = self.user_id
		all_user_playlists = f"https://api.spotify.com/v1/users/{user_id}/playlists"
		playlist_meta = pd.DataFrame()
		playlists_URL = f'{all_user_playlists}'
		r = requests.get(playlists_URL, headers=headers)
		data = r.json()
		playlists = data['total']
		for playlist in range(playlists):
			r = requests.get(playlists_URL, headers = headers, params={('limit','1'),('offset',f'{playlist}')})
			data = r.json()
			df_playlist = pd.DataFrame(
				{"name": data['items'][0]["name"],
				"id": data['items'][0]["id"],
				"total_tracks": data['items'][0]["tracks"]["total"],
				"owner": data['items'][0]['owner']["display_name"]}, index = [playlist])
			playlist_meta = pd.concat([playlist_meta, df_playlist], axis = 0)
		return playlist_meta

	def get_playlist_tracks(self):
		user_info = self.user_info()
		params = self.params()
		playlists = self.get_user_playlists()
		headers = self.headers()
		path = str(os.getcwd()) + "\\" + user_info["display_name"] + "\\"
		if not os.path.exists(path):
			os.mkdir(path)
		print(playlists)
		playlist_number = int(input("Enter your playlist: "))
		print(playlists.iloc[[playlist_number]],"\n------------------------------\n\n\n")
		playlist_id = playlists.iloc[playlist_number][1]
		playlist_name = re.sub(r'\W+', '', playlists.iloc[playlist_number][0])
		playlist_name = playlist_name.replace(["/","\\","?"], '')
		r = requests.get(f'https://api.spotify.com/v1/playlists/{playlist_id}/tracks', headers=headers)
		data = r.json()
		songs = data["total"]
		song_metadata = pd.DataFrame()
		for song in range(songs):
			if song != 0 and song%100 == 0:
					r = requests.get(data["next"], headers=headers, params=params)
					data = r.json()
			else:
				r = requests.get(f'https://api.spotify.com/v1/playlists/{playlist_id}/tracks', headers=headers, params=params)
				data = r.json()
			song_meta = spotify.song_metainfo(song, data)
			song_metadata = pd.concat([song_metadata, song_meta], axis = 0)		
		song_metadata.to_excel(f'{path}{playlist_name}.xlsx', encoding='utf-16', index = False, engine='xlsxwriter')
		print(f'{path}{playlist_name}.xlsx <-- Ready')
		return

	def song_metainfo(self, song, data):
		album_name = data["items"][0]["track"]["album"]["name"]
		album_id = data["items"][0]["track"]["album"]["id"]
		if len(data["items"][0]["track"]["album"]["images"]) != 0:
			album_art = data["items"][0]["track"]["album"]["images"][0]["url"]
		else:
			album_art = None
		track_name = data["items"][0]["track"]["name"]
		track_id = data["items"][0]["track"]["id"]
		artists = [data["items"][0]["track"]["artists"][x]["name"] for x in range(len(data["items"][0]["track"]["artists"]))]
		artist_id = [data["items"][0]["track"]["artists"][y]["id"] for y in range(len(data["items"][0]["track"]["artists"]))]
		return (pd.DataFrame({
			"track_name":track_name,
			"track_id": track_id,
			"artists": str(artists),
			"artist_id": str(artist_id),
			"album_name": album_name,
			"album_id": album_id,
			"album_art": album_art},
			index = [song]))

	def everything(self):
		user_info = self.user_info()
		headers = self.headers()
		playlists = self.get_user_playlists()
		playlists["name"] = playlists["name"].str.replace("\W+\s", "").astype("unicode")
		path = str(os.getcwd()) + "\\" + user_info["display_name"] + "\\"
		if not os.path.exists(path):
			os.mkdir(path)
		for playlist_id, playlist_name in zip(playlists["id"],playlists["name"].replace("[/,\,?]", "")):
			song_metadata = pd.DataFrame()
			params = self.params()
			r = requests.get(f'https://api.spotify.com/v1/playlists/{playlist_id}/tracks', headers=headers, params=params)
			data = r.json()
			songs = data["total"]
			for song in range(songs):
				params = {('fields','items(track(name,id,album(name,id,images(url)),artists(name,id)))'), ("limit","1"), ('offset',f'{song}')}
				r = requests.get(f'https://api.spotify.com/v1/playlists/{playlist_id}/tracks', headers=headers, params=params)
				data = r.json()
				# sleep(randint(10,100))
				song_meta = spotify.song_metainfo(song, data)
				sleep(.1)
				song_metadata = pd.concat([song_metadata, song_meta], axis = 0)
			print(playlist_name)
			# song_metadata.to_excel(f'{path}{playlist_name}.xlsx', encoding='utf-16', index = False, engine='xlsxwriter')
			# print(f'{path}{playlist_name}.xlsx <-- Ready')
		return 

spotify = SpotifyAPI("https://open.spotify.com/user/sy0kg7sbkw9yb3idmp9skxyf8")
spotify.everything()
# print(spotify.get_user_playlists())