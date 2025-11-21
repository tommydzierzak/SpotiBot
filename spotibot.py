import logging

from telegram import ForceReply, Update, Bot
from telegram.ext import Application, CommandHandler, ContextTypes, MessageHandler, filters

import os
import glob

import eyed3

import spotipy
from spotipy.oauth2 import SpotifyOAuth

import requests

import urllib.request

import yt_dlp

SPOTIPY_CLIENT_ID = os.getenv("SPOTIPY_CLIENT_ID")
SPOTIPY_CLIENT_SECRET = os.getenv("SPOTIPY_CLIENT_SECRET")
REDIRECT_URI = os.getenv("REDIRECT_URI")
telegramToken = os.getenv("telegramToken")
adminChatID = os.getenv("adminChatID")
playlistID = os.getenv("playlistID")
bannedPlaylistID = os.getenv("bannedPlaylistID")

MESSAGE1 = os.getenv('MESSAGE1')
MESSAGE2 = os.getenv('MESSAGE2')
MESSAGE3 = os.getenv('MESSAGE3')
MESSAGE4 = os.getenv('MESSAGE4')
STICKER1 = os.getenv('STICKER1')
STICKER2 = os.getenv('STICKER2')
STICKER3 = os.getenv('STICKER3')
STICKER4 = os.getenv('STICKER4')


scope = "playlist-modify-private"

authorizedFlag = False
authURL = ""

auth_manager = SpotifyOAuth(client_id=SPOTIPY_CLIENT_ID, client_secret=SPOTIPY_CLIENT_SECRET, redirect_uri=REDIRECT_URI, scope=scope, open_browser=False)


def check_auth(auth_manager):
    global authorizedFlag
    global authURL
    if auth_manager.get_cached_token() == None:
        print("No cached token need to Authorize")
        authURL = auth_manager.get_authorize_url()
        authorizedFlag = False
    else:
        print("Cached Token found, testing...")
        try:
            sp = spotipy.Spotify(auth_manager = auth_manager)
            sp.track("spotify:track:4PTG3Z6ehGkBFwjybzWkR8")
        except:
            print("Cached oauth seems to be broken, deleting and sending back for reauth")
            os.remove(".cache")
            authorizedFlag = False
            check_auth(auth_manager)
            #break
        else:
            print("Authorization looks good")
            authorizedFlag = True


def get_songs_in_PL(playlist_id, sp): # need to pass sp in so playlist check can work
    r = sp.playlist_tracks(playlist_id) # TODO this could certainly be optimized
    t = r['items']
    ids = []
    while r['next']:
        r = sp.next(r)
        t.extend(r['items'])
    for s in t: ids.append(s["track"]["id"])
    return ids


def grabMP3(link):
    print("grabbing")

    sp = spotipy.Spotify(auth_manager = auth_manager)

    data = sp.track(link)

    uriToAdd = [data['uri']]

    print(uriToAdd)

    banURIs = get_songs_in_PL(bannedPlaylistID, sp)

    if data['id'] in banURIs:
        bannedSongFlag = True
        addedToPlaylistFlag = False
    else:
        bannedSongFlag = False

        if data['id'] not in get_songs_in_PL(playlistID, sp):
            sp.playlist_add_items(playlistID, uriToAdd)  # Add to playlist, link must be in list format
            addedToPlaylistFlag = True
        else:
            addedToPlaylistFlag = False
            print(f"Song {link} is already in the playlist.")

    if data['preview_url'] and data['album']['images'][0]['url'] is not None:
        img_data = requests.get(data['album']['images'][0]['url']).content
        print("got image data")
        print(data['preview_url'])
        audio_data = requests.get(data['preview_url']).content
        os.makedirs(os.path.dirname("dl/"), exist_ok=True)  # Open throws an error if the directory doesn't exist yet
        with open(('dl/preview.mp3'), 'wb') as handler:
            handler.write(audio_data)
        print("got audio")
        audio = eyed3.load('dl/preview.mp3')
        if (audio.tag == None):
            audio.initTag()

        audio.initTag()
        audio.tag.title = data["name"]
        audio.tag.album = data["album"]["name"]
        audio.tag.artist = data["artists"][0]["name"]
        audio.tag.album_artist = data["artists"][0]["name"]
        audio.tag.images.set(3, img_data, 'image/jpeg')
        audio.tag.save(version=eyed3.id3.ID3_V2_3)
        previewFlag=True
    else:
        previewFlag=False
        print("no preview found")

    return addedToPlaylistFlag, previewFlag, bannedSongFlag


def soundCloud(link):

    # Variable to store the file location
    # global downloaded_file_path = None

    # Define a progress hook to capture the file path
    def progress_hook(d):
        global downloaded_file_path
        if d['status'] == 'finished':
            downloaded_file_path = d['filename']
            print(f"Downloaded to: {downloaded_file_path}")


    ydl_opts = {
        'format': 'mp3/bestaudio/best',
        'writethumbnail': True,
        'embedmetadata': True,
        'outtmpl': 'dl/%(title)s.%(ext)s',
        'postprocessors': [
            {'key': 'FFmpegMetadata'},
            {'key': 'EmbedThumbnail'},
        ],
        'progress_hooks': [progress_hook],  # Hook to capture download progress
    }

    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        ydl.download(link)


async def echo(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    global auth_manager
    global authorizedFlag
    if authorizedFlag:
    #print(update.message)
        if update.message.text.startswith("https://spotify.link") or update.message.text.startswith("https://open.spotify.com"):
            if update.message.text.startswith("https://spotify.link"):
                with urllib.request.urlopen(update.message.text) as response:
                    link = response.url
            else:
                link = update.message.text
            print(link)
            try:
                addedToPlaylistFlag, previewFlag, bannedSongFlag = grabMP3(link)
            except:
                print("Some kind of error in grabMP3")
            else:
                if bannedSongFlag:
                    await update.message.reply_sticker(STICKER4)
                    await update.message.reply_text(MESSAGE4)
                elif addedToPlaylistFlag:
                    if previewFlag:
                        await update.message.reply_document("dl/preview.mp3")
                    else:
                        await update.message.reply_sticker(STICKER1)
                        #await update.message.reply_text(MESSAGE1)
                else:
                    if previewFlag:
                        await update.message.reply_sticker(STICKER2)
                        await update.message.reply_document("dl/preview.mp3", caption=MESSAGE2)
                    else:
                        await update.message.reply_sticker(STICKER3)
                        await update.message.reply_text(MESSAGE3)
        elif update.message.text.startswith("https://on.soundcloud") or update.message.text.startswith("https://soundcloud"):
            link = update.message.text
            try:
                soundCloud(link)
                print(downloaded_file_path)
            except:
                pass
            else:
                await update.message.reply_document(str(downloaded_file_path))
                files = glob.glob('dl/*')
                for f in files:
                    os.remove(f)
    else:
        if update.message.text.startswith(REDIRECT_URI):
            state, code = SpotifyOAuth.parse_auth_response_url(update.message.text)
            auth_manager.get_access_token(code)
            check_auth(auth_manager)
        else:
            await context.bot.send_message(adminChatID, f"Need to authorize. Sign in with the following link: {authURL}\nThen send me the link you're forwarded to.")




def main() -> None:
    """Start the bot."""

    check_auth(auth_manager)

    application = Application.builder().token(telegramToken).build()

    application.add_handler(MessageHandler(filters.TEXT, echo))

    application.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == "__main__":
    main()
