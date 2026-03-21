api_key = "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"


# pip install groq sounddevice scipy requests simpleaudio
import io
import os
import wave
import tempfile
import sounddevice as sd
from scipy.io.wavfile import write
import simpleaudio as sa
from groq import Groq

# client = Groq(api_key=os.environ["GROQ_API_KEY"])
client = Groq(api_key=api_key)

SYSTEM_PROMPT = "You are a helpful voice assistant. Keep replies brief and natural."

def record_wav(seconds=4, sample_rate=16000):
    audio = sd.rec(int(seconds * sample_rate), samplerate=sample_rate, channels=1, dtype="int16")
    sd.wait()
    tmp = tempfile.NamedTemporaryFile(suffix=".wav", delete=False)
    write(tmp.name, sample_rate, audio)
    return tmp.name

def transcribe(path):
    with open(path, "rb") as f:
        tr = client.audio.transcriptions.create(
            file=(os.path.basename(path), f.read()),
            model="whisper-large-v3"
        )
    return tr.text

def chat(user_text):
    resp = client.chat.completions.create(
        model="openai/gpt-oss-20b",
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": user_text},
        ],
    )
    return resp.choices[0].message.content

def speak(text, out_path="reply.wav"):
    audio = client.audio.speech.create(
        model="playai-tts",
        voice="Fritz-PlayAI",
        input=text,
        response_format="wav",
    )
    audio.write_to_file(out_path)
    return out_path

def play_wav(path):
    wave_obj = sa.WaveObject.from_wave_file(path)
    play_obj = wave_obj.play()
    play_obj.wait_done()

if __name__ == "__main__":
    wav_path = record_wav()
    heard = transcribe(wav_path)
    print("You:", heard)

    reply = chat(heard)
    print("Assistant:", reply)

    out = speak(reply)
    play_wav(out)