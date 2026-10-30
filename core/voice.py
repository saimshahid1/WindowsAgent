import asyncio
import os
import queue
import re
import tempfile

import av
import edge_tts
import numpy as np
import sounddevice as sd
from faster_whisper import WhisperModel

SAMPLE_RATE = 16000


class SpeechToText:
    def __init__(self, model_size="small"):
        print("Loading speech model...")
        self.model = WhisperModel(model_size, device="cpu", compute_type="int8")

    def record(self):
        q = queue.Queue()

        def callback(indata, frames, time, status):
            q.put(indata.copy())

        input("Press Enter and speak...")
        with sd.InputStream(samplerate=SAMPLE_RATE, channels=1, dtype="float32", callback=callback):
            input("Listening... press Enter to stop.")

        chunks = []
        while not q.empty():
            chunks.append(q.get())
        if not chunks:
            return np.zeros(0, dtype=np.float32)
        return np.concatenate(chunks).flatten()

    def transcribe(self, audio):
        if audio.size == 0:
            return ""
        segments, _ = self.model.transcribe(audio, beam_size=1, vad_filter=True)
        return " ".join(s.text.strip() for s in segments).strip()

    def listen(self):
        return self.transcribe(self.record())


class TextToSpeech:
    def __init__(self, voice="en-US-AriaNeural"):
        self.voice = voice

    def _clean(self, text):
        text = re.sub(r"[*#|`_>]", " ", text)
        text = re.sub(r"[^\x00-\x7F\u0600-\u06FF]", " ", text)
        text = re.sub(r"\s+", " ", text)
        return text.strip()

    def _play_mp3(self, path):
        container = av.open(path)
        stream = container.streams.audio[0]
        frames = [frame.to_ndarray() for frame in container.decode(stream)]
        rate = stream.rate
        container.close()
        if not frames:
            return
        audio = np.concatenate(frames, axis=1).T.astype(np.float32)
        sd.play(audio, rate)
        sd.wait()

    def speak(self, text):
        text = self._clean(text)
        if not text:
            return
        fd, path = tempfile.mkstemp(suffix=".mp3")
        os.close(fd)
        try:
            asyncio.run(edge_tts.Communicate(text, self.voice).save(path))
            self._play_mp3(path)
        except Exception as e:
            print(f"  [voice error] {e}")
        finally:
            os.remove(path)