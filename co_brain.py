import os
import sys
import random
import threading
import time

# Cấu hình tự động thêm thư mục gốc dự án vào Python Path để tránh lỗi Unresolved Import
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from Automation.Automation_Brain import Auto_main_brain, clear_file
from NetHyTechSTT.listen import listen
from TextToSpeech.Fast_DF_TTS import speak
from Data.DLG_Data import online_dlg, offline_dlg

# Sửa lỗi Import Battery: Thử import check_plug hoặc battery_Alert an toàn
try:
    from Automation.Battery import check_plug
except ImportError:
    try:
        from Automation.Battery import battery_Alert
    except ImportError:
        pass

from Time_Operations.brain import input_manage, input_manage_Alam

# Import module Vision an toàn
try:
    from Vision.Vbrain import capture_image_and_save, encode_image_to_base64, vision_brain
except ImportError:
    pass

try:
    from Vision.MVbrain import capture_image_and_save as capture_mobile_image
    from Vision.MVbrain import mobile_vision_brain
except ImportError:
    try:
        from Vision.MVBrain import capture_image_and_save as capture_mobile_image
        from Vision.MVBrain import mobile_vision_brain
    except ImportError:
        pass

from Weather_Check.check_weather import get_weather_by_address
from Whatsapp_automation.wa import send_msg_wa
from TextToImage.gen_image import generate_image
from Features.mike_health import mike_health
from Features.speaker_health import speaker_health_test
from Features.br_persentage import check_br_persentage
from Features.set_br import set_brightness_windows
from Features.set_get_volume import get_volume_windows, set_volume_windows
from Features.check_running_app import check_running_app
from jarvis_runtime import DEFAULT_AGENT, DEFAULT_MODEL, DEFAULT_TOOLS, get_runtime
from branding import ASSISTANT_NAME


def Main_Brain(prompt, model=None, agent=DEFAULT_AGENT, tools=None):
    try:
        result = get_runtime().ask_full(
            prompt,
            model=model,
            agent=agent,
            tools=tools if tools is not None else DEFAULT_TOOLS,
        )
        return result.get("content", "")
    except Exception as e:
        return f"OpenJarvis runtime error: {e}"


numbers = ["1:", "2:", "3:", "4:", "5:", "6:", "7:", "8:", "9:"]
spl_numbers = ["11:", "12:"]

ran_online_dlg = None
ran_offline_dlg = None


def _init_random_dialogs():
    global ran_online_dlg, ran_offline_dlg
    try:
        ran_online_dlg = random.choice(online_dlg)
    except (IndexError, ValueError):
        ran_online_dlg = ""
    try:
        ran_offline_dlg = random.choice(offline_dlg)
    except (IndexError, ValueError):
        ran_offline_dlg = ""


def normalize_request(text):
    request = text.strip().lower()
    for wake_phrase in (f"hey {ASSISTANT_NAME.lower()}", ASSISTANT_NAME.lower()):
        if request.startswith(wake_phrase):
            return request[len(wake_phrase):].lstrip(" ,.!?")
    return request


def respond_to_user(text, log_file_path, model=None, agent=DEFAULT_AGENT, tools=None):
    # Flush the user turn first so the desktop UI can show that the request was
    # received while the local model is still generating its answer.
    with open(log_file_path, "a", encoding="utf-8") as log_file:
        log_file.write("\nYou : " + text + "\n")
        log_file.flush()

    try:
        result = get_runtime().ask_full(
            text,
            model=model,
            agent=agent,
            tools=tools if tools is not None else DEFAULT_TOOLS,
        )
        response = result.get("content", "")
    except Exception as exc:
        result = {}
        response = f"OpenJarvis runtime error: {exc}"

    with open(log_file_path, "a", encoding="utf-8") as log_file:
        log_file.write(f"{ASSISTANT_NAME.lower()} : {response}\n")
        log_file.write(
            f"runtime : {result.get('engine', 'ollama')} / "
            f"{result.get('model', model or DEFAULT_MODEL)}\n"
        )
        for tool_result in result.get("tool_results", []):
            tool_name = tool_result.get("tool_name", "unknown")
            success = bool(tool_result.get("success"))
            log_file.write(
                f"tool : {tool_name} / {'ok' if success else 'failed'}\n"
            )
            details = tool_result.get("result", "")
            if isinstance(details, dict):
                details = details.get("result", details.get("target", ""))
            details = str(details).replace("\n", " ")[:240]
            log_file.write(
                f"action : {time.strftime('%Y-%m-%d %H:%M:%S')} | {tool_name} | "
                f"{details} | {'ok' if success else 'failed'}\n"
            )
        log_file.flush()
    # Speak asynchronously so the listener stays responsive.
    threading.Thread(target=speak, args=(response,), daemon=True).start()


def check_inputs(stop_event=None):
    _init_random_dialogs()
    previous_input_text = ""
    base_dir = os.path.dirname(os.path.abspath(__file__))
    input_file_path = os.path.join(base_dir, "input.txt")
    log_file_path = os.path.join(base_dir, "log.txt")

    while stop_event is None or not stop_event.is_set():
        if not os.path.exists(input_file_path):
            time.sleep(0.1)
            continue

        try:
            with open(input_file_path, "r", encoding="utf-8") as file:
                input_text = file.read().lower().strip()
        except (OSError, UnicodeError):
            time.sleep(0.1)
            continue

        if not input_text:
            previous_input_text = ""
            time.sleep(0.05)
            continue

        if input_text and input_text != previous_input_text:
            previous_input_text = input_text
            # Consume each completed utterance once, allowing the same command
            # to be spoken again after the listener has written it.
            try:
                with open(input_file_path, "r+", encoding="utf-8") as file:
                    if file.read().strip().lower() == input_text:
                        file.seek(0)
                        file.truncate()
            except OSError:
                pass
            output_text = normalize_request(input_text)
            if not output_text:
                time.sleep(0.05)
                continue
            if output_text.startswith("tell me"):
                output_text = output_text.replace(" p.m.", "PM").replace(" a.m.", "AM")
                if "11:" in output_text or "12:" in output_text:
                    input_manage(output_text)
                    clear_file()
                else:
                    for number in numbers:
                        if number in output_text:
                            output_text = output_text.replace(number, f"0{number}")
                            input_manage(output_text)
                            clear_file()

            elif output_text.startswith("set alarm"):
                output_text = output_text.replace(" p.m.", "PM").replace(" a.m.", "AM")
                if "11:" in output_text or "12:" in output_text:
                    input_manage_Alam(output_text)
                    clear_file()
                else:
                    for number in numbers:
                        if number in output_text:
                            output_text = output_text.replace(number, f"0{number}")
                            input_manage_Alam(output_text)
                            clear_file()

            elif (output_text.startswith(("create ", "find file", "search file", "read file", "delete file",
                                          "copy file", "move file", "rename file", "tìm file", "đọc file",
                                          "xóa file", "sao chép file", "di chuyển file", "analyze image",
                                          "describe image", "what is in image", "phân tích ảnh", "mô tả ảnh")) and
                  ("file" in output_text or "tệp" in output_text or "tập tin" in output_text or
                   "image" in output_text or "ảnh" in output_text)):
                respond_to_user(output_text, log_file_path)

            elif "what is this" in output_text or "what can you see" in output_text:
                image_path = "captured_image.png"
                try:
                    if 'capture_image_and_save' in globals() and capture_image_and_save(image_path):
                        encoded_image = encode_image_to_base64(image_path)
                        answer = vision_brain(encoded_image, prompt=output_text)
                        speak(answer)
                    else:
                        speak("I could not capture an image from the camera.")
                except Exception as exc:
                    speak(f"Local vision failed: {exc}")

            elif "what is in front of mobile camera" in output_text or "what can you see use mobile camera" in output_text:
                image_path = "captured_image.png"
                try:
                    if 'capture_mobile_image' in globals() and capture_mobile_image(image_path):
                        encoded_image = encode_image_to_base64(image_path)
                        answer = mobile_vision_brain(encoded_image, prompt=output_text)
                        speak(answer)
                    else:
                        speak("I could not capture an image from the mobile camera.")
                except Exception as exc:
                    speak(f"Mobile vision failed: {exc}")

            elif "check weather" in output_text:
                text = output_text.replace("check weather in", "")
                ans = get_weather_by_address(text)
                speak(ans)

            elif "send message on whatsapp" in output_text:
                send_msg_wa()

            elif "generate image" in output_text:
                text = output_text.replace("generate image", "").strip()
                generate_image(text)
                speak("image generated successfully")

            elif "check mike" in output_text or "check mike health" in output_text or "check microphone" in output_text:
                mike_health()

            elif "check speaker health" in output_text or "check speaker" in output_text:
                speaker_health_test()

            elif "check brightness percentage" in output_text:
                check_br_persentage()

            elif "set brightness percentage" in output_text:
                set_val = output_text.replace("set brightness percentage", "").strip()
                set_brightness_windows(int(set_val))

            elif "check volume level" in output_text:
                get_volume_windows()

            elif "set volume level" in output_text:
                set_val = output_text.replace("set volume level", "").replace("%", "").strip()
                set_volume_windows(int(set_val))

            elif "check running application" in output_text:
                check_running_app()
            elif (output_text.startswith(("open ", "search ", "close ", "play ", "stop ", "pause "))
                  or "check battery" in output_text
                  or "check volume" in output_text
                  or "set volume" in output_text
                  or "check brightness" in output_text
                  or "set brightness" in output_text
                  or "check running application" in output_text):
                Auto_main_brain(output_text, stop_event=stop_event)
            else:
                # Ordinary questions and conversation must reach the language model;
                # the automation router has no conversational fallback.
                respond_to_user(output_text, log_file_path)
        time.sleep(0.05)


def AstraVoiceLoop(status_callback=None, stop_event=None, transcript_callback=None,
                   audio_level_callback=None, speech_activity_callback=None):
    clear_file()

    if stop_event is None:
        stop_event = threading.Event()

    def run_listener():
        try:
            listen(
                stop_event=stop_event,
                status_callback=status_callback,
                on_transcript=transcript_callback,
                on_audio_level=audio_level_callback,
                on_speech_activity=speech_activity_callback,
            )
        except Exception as exc:
            if status_callback:
                try:
                    status_callback(f"Không thể khởi động microphone: {exc}", "error")
                except Exception:
                    pass
            stop_event.set()

    t1 = threading.Thread(target=run_listener)
    t2 = threading.Thread(target=check_inputs, args=(stop_event,))
    t1.start()
    t2.start()
    t1.join()
    stop_event.set()
    t2.join()


if __name__ == "__main__":
    AstraVoiceLoop()
