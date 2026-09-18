from voice import Voice

v = Voice()
print("Ready:", v.is_ready())

segments = [
    {"text": "Hey there!", "tone": "excited"},
    {"text": "I missed you so much. I dont know what to do", "tone": "sad"},
    {"text": "How are you feeling today?", "tone": "shout"},
]

path = v.synthesize_segments_to_wav(segments)
print("Output:", path)

if path:
    import os
    os.startfile(path)   # Windows — plays the file