import pywhatkit as kit
import datetime
import os
import time
from TextToSpeech.Fast_DF_TTS import speak
from os import getcwd
from branding import OWNER_NAME

WHATSAPP_NUMBER = os.environ.get("ASTRA_DANNZ_WHATSAPP", "").strip()

def clear_file():
    with open(f"{getcwd()}\\input.txt","w") as file:
        file.truncate(0)
        
def send_msg_wa():
    if not WHATSAPP_NUMBER:
        speak("Set ASTRA_DANNZ_WHATSAPP to your WhatsApp number before sending messages.")
        return

    speak(f"Do you want to send a message to {OWNER_NAME}?")
    output_text = ""
    while True:
        with open("input.txt","r") as file:
            input_text = file.read().lower() 
        if input_text != output_text:
            output_text = input_text
            if output_text.startswith("send to") or output_text.startswith("send tu"):
                recipient = output_text.replace("send to", "", 1).replace("send tu", "", 1).strip()
                if OWNER_NAME.lower() in recipient:
                    speak("By the way what is the message , sir ?")
                    while True:
                       with open("input.txt","r") as file:
                          input_text = file.read().lower() 
                          if input_text != output_text:
                              output_text = input_text
                              if output_text.startswith("message is"):
                                  message = output_text.replace("message is", "", 1).strip()
                                  send_time = datetime.datetime.now() + datetime.timedelta(minutes=1)
                                  kit.sendwhatmsg(WHATSAPP_NUMBER, message, send_time.hour, send_time.minute)
                                  speak("message send successfully")
                                  return
                       time.sleep(0.1)
        time.sleep(0.1)


