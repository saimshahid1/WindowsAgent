import queue
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