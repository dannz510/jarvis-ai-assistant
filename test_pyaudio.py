import pyaudio
p = pyaudio.PyAudio()
print('PyAudio OK')
print('Devices:', p.get_device_count())
for i in range(p.get_device_count()):
    info = p.get_device_info_by_index(i)
    if info['maxInputChannels'] > 0:
        print(f'  Input: {info["name"]} (ch={info["maxInputChannels"]})')
p.terminate()
