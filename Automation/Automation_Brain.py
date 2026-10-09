from Automation.open_App import open_App
from Automation.Web_Open import openweb
import pyautogui as gui
from Automation.Play_Music_YT import play_music_on_youtube
from TextToSpeech import Fast_DF_TTS
from Automation.playmusic_Sfy import play_music_on_spotify
from Automation.Battery import check_percentage
from os import getcwd
import time
from Automation.tab_automation import perform_browser_action
from Automation.Youtube_play_back import perform_media_action
import pywhatkit
from Automation.scrool_system import perform_scroll_action
import threading
from threading import Event
from TextToSpeech.Fast_DF_TTS import speak
import re

def play():
    gui.press("space")
    
def search_google(text):
    pywhatkit.search(text)

def close():
    gui.hotkey('alt','f4')
    
def search(text):
    gui.press("/")
    time.sleep(0.3)
    gui.write(text)

def Open_Brain(text):
    request = str(text).strip()
    if "website" in request.casefold():
        website = re.sub(r"^open\s+website(?:\s+named)?\s*", "", request, flags=re.I).strip()
        if openweb(website):
            speak(f"Opened {website} website.")
        else:
            speak(f"I do not have a trusted address for {website}.")
    else:
        application = re.sub(r"^open\s+", "", request, flags=re.I).strip()
        try:
            open_App(application)
            speak(f"Opened {application}.")
        except (OSError, RuntimeError, ValueError) as exc:
            speak(f"I could not open {application}: {exc}")
        
def clear_file():
    with open(f"{getcwd()}\\input.txt","w") as file:
        file.truncate(0)

def _wait_for_song_name(stop_event=None, timeout_seconds=20):
    """Wait briefly for the next recognized phrase without trapping voice control."""
    stop_event = stop_event or Event()
    deadline = time.monotonic() + timeout_seconds
    last_text = ""
    while not stop_event.is_set() and time.monotonic() < deadline:
        try:
            with open("input.txt", "r", encoding="utf-8") as file:
                current_text = file.read().strip().lower()
        except (OSError, UnicodeError):
            current_text = ""
        if current_text and current_text != last_text:
            clear_file()
            return current_text
        time.sleep(0.1)
    return ""


def Auto_main_brain(text, stop_event=None):
   try: 
    if text.startswith("open"):
        Open_Brain(text)
    elif "close" in text:
        close()
    elif "play music" in text or "play music on youtube" in text:
        Fast_DF_TTS.speak("Which song would you like to play?")
        clear_file()
        song = _wait_for_song_name(stop_event)
        if song:
            play_music_on_youtube(song)
        elif stop_event is None or not stop_event.is_set():
            Fast_DF_TTS.speak("I did not receive a song name. Please try again.")
        
    elif "play some music" in text or "play music on spotify" in text:
        Fast_DF_TTS.speak("Which song would you like to play on Spotify?")
        clear_file()
        song = _wait_for_song_name(stop_event)
        if song:
            play_music_on_spotify(song)
        elif stop_event is None or not stop_event.is_set():
            Fast_DF_TTS.speak("I did not receive a song name. Please try again.")

    elif "check battery percentage" in text or "check battery level" in text:
        check_percentage()
    elif text.startswith("search"):
        text = text.replace("search","")
        text = text.strip()
        t1 = threading.Thread(target=speak,args=(f"doing research about {text}",))
        t2 = threading.Thread(target=search,args=(text,))
        t1.start()
        t2.start()
        t1.join()
        t2.join()
        time.sleep(0.5)
        gui.press("enter")
    elif "search in google" in text:
        text = text.replace("search in google","")
        t1 = threading.Thread(target=speak,args=(f"performing research about {text} in google search engine",))
        t2 = threading.Thread(target=search_google,args=(text,))
        t1.start()
        t2.start()
        t1.join()
        t2.join()
    elif "play" in text or "stop" in text or "pause" in text:
        play()
    else:
        perform_browser_action(text)
        perform_media_action(text)
        perform_scroll_action(text)

   except Exception as e:
       print(f"error : {e}")

