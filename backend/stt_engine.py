import os
import io
import json
import wave
from pathlib import Path

try:
    import speech_recognition as sr
except ImportError:
    sr = None

try:
    from vosk import Model, KaldiRecognizer
except ImportError:
    Model = None
    KaldiRecognizer = None

# Locate the Vosk models inside ArKon-Personal-AI project
ARKON_VOSK_DIR = Path(r"c:\Users\aryan\OneDrive\Desktop\Antigravity Projects\ArKon-Personal-AI\ArKon-Personal-AI\Backend\Vosk")
_VOSK_MODEL_CACHE = {}

def get_vosk_model(lang: str):
    if Model is None:
        raise ImportError("Vosk library is not installed in this Python environment.")
        
    if lang not in _VOSK_MODEL_CACHE:
        model_name = "vosk-model-small-hi-0.22" if lang == "hi" else "vosk-model-small-en-us-0.15"
        model_path = ARKON_VOSK_DIR / model_name
        
        if not model_path.exists():
            raise FileNotFoundError(f"Vosk model not found at: {model_path}")
            
        print(f"[STT] Loading local Vosk model: {model_name}")
        _VOSK_MODEL_CACHE[lang] = Model(str(model_path))
        
    return _VOSK_MODEL_CACHE[lang]

def transcribe_microphone(lang: str = "en") -> str:
    """
    Listens to the microphone and transcribes speech using local Vosk models.
    """
    if sr is None or Model is None:
        print("[STT] PyAudio/SpeechRecognition or Vosk is not available.")
        return ""
        
    # Get models
    try:
        model = get_vosk_model(lang)
    except Exception as e:
        print(f"[STT] Error loading Vosk model: {e}")
        # If specific language model fails, try fallback to english
        if lang == "hi":
            try:
                model = get_vosk_model("en")
                lang = "en"
            except Exception:
                return ""
        else:
            return ""

    r = sr.Recognizer()
    r.energy_threshold = 300
    r.dynamic_energy_threshold = True
    
    # Use default system microphone
    mic = sr.Microphone()
    
    try:
        print(f"[STT] Listening on microphone (lang={lang})...")
        with mic as source:
            # Listen for up to 5 seconds of silence or 10 seconds of speech
            audio = r.listen(source, timeout=5, phrase_time_limit=10)
            
        print("[STT] Processing audio using local Vosk...")
        # Vosk requires 16000Hz mono 16-bit PCM wav data
        wav_bytes = audio.get_wav_data(convert_rate=16000, convert_width=2)
        
        # Run Kaldi recognizer
        wav_file = wave.open(io.BytesIO(wav_bytes), "rb")
        n_channels = wav_file.getnchannels()
        sample_rate = wav_file.getframerate()
        data = wav_file.readframes(wav_file.getnframes())
        
        if n_channels == 2:
            print("[STT] Converting stereo microphone input to mono PCM...")
            # Keep only the left channel (every first 2 bytes of each 4-byte frame)
            mono_data = bytearray(len(data) // 2)
            mono_data[0::2] = data[0::4]
            mono_data[1::2] = data[1::4]
            data = bytes(mono_data)
            n_channels = 1
            
        print(f"[STT] Decoding {len(data)} bytes of PCM (channels={n_channels}, rate={sample_rate})...")
        rec = KaldiRecognizer(model, sample_rate)
        rec.AcceptWaveform(data)
        
        result_json = json.loads(rec.FinalResult())
        text = result_json.get("text", "").strip()
        
        print(f"[STT] Local Speech Recognized: '{text}'")
        return text
        
    except sr.WaitTimeoutError:
        print("[STT] Listening timed out (no speech detected).")
        return ""
    except Exception as e:
        print(f"[STT] Speech recognition exception: {e}")
        return ""
