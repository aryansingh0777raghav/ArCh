import os
import re
import tempfile
import wave
import subprocess
from pathlib import Path

try:
    import piper
except ImportError:
    piper = None

# Locate the Piper models inside ArKon-Personal-AI project
ARKON_PIPER_DIR = Path(r"c:\Users\aryan\OneDrive\Desktop\Antigravity Projects\ArKon-Personal-AI\ArKon-Personal-AI\Backend\Piper_tts")
_PIPER_VOICE_CACHE = {}

def clean_markdown_for_speech(md_text: str) -> str:
    """
    Strips markdown formatting, code blocks, links, and citation brackets
    so the TTS reads a clean human-natural sentence.
    """
    if not md_text:
        return ""
    # Remove code blocks
    text = re.sub(r'```[\s\S]*?```', '', md_text)
    # Remove inline code
    text = re.sub(r'`[^`\n]+`', '', text)
    # Remove tables (lines starting and ending with |)
    lines = text.split('\n')
    cleaned_lines = []
    for line in lines:
        stripped = line.strip()
        if stripped.startswith('|') and stripped.endswith('|'):
            continue
        cleaned_lines.append(line)
    text = "\n".join(cleaned_lines)
    # Remove link markdown: [text](url) -> text
    text = re.sub(r'\[([^\]]+)\]\([^)]+\)', r'\1', text)
    # Remove citation pills: [1], [2], [12] -> empty
    text = re.sub(r'\[\d+\]', '', text)
    # Remove bold / italic markers
    text = re.sub(r'\*\*([^*]+)\*\*', r'\1', text)
    text = re.sub(r'\*([^*]+)\*', r'\1', text)
    text = re.sub(r'__([^_]+)__', r'\1', text)
    text = re.sub(r'_([^_]+)_', r'\1', text)
    # Remove heading tags
    text = re.sub(r'^#+\s+', '', text, flags=re.MULTILINE)
    # Collapse multiple spaces and newlines
    text = re.sub(r'\s+', ' ', text).strip()
    return text

def detect_language(text: str) -> str:
    """
    Detects if the query is in Hindi/Hinglish or English.
    """
    # Devanagari range check
    if any("\u0900" <= ch <= "\u097F" for ch in text):
        return "hi"
    
    # Roman Hindi/Hinglish keywords
    roman_hindi_words = {
        "kya", "kaise", "kaisa", "kaisi", "kyu", "kyun", "kyon", "nahi", "nhi",
        "mujhe", "mera", "meri", "mere", "tum", "aap", "hum", "hain", "hai",
        "bolo", "batao", "btayo", "btao", "kr", "karo", "kar", "chahiye", "ho", "naam"
    }
    
    words = set(re.findall(r"\w+", text.lower()))
    if words.intersection(roman_hindi_words):
        return "hi"
        
    return "en"

def get_piper_voice(lang: str):
    if piper is None:
        raise ImportError("Piper library is not installed in this Python environment.")
        
    if lang not in _PIPER_VOICE_CACHE:
        model_name = "hi_IN-pratham-medium.onnx" if lang == "hi" else "en_US-joe-medium.onnx"
        model_path = ARKON_PIPER_DIR / model_name
        
        if not model_path.exists():
            raise FileNotFoundError(f"Piper ONNX model not found at: {model_path}")
            
        print(f"[TTS] Loading local Piper model: {model_name}")
        _PIPER_VOICE_CACHE[lang] = piper.PiperVoice.load(str(model_path))
        
    return _PIPER_VOICE_CACHE[lang]

def synthesize_sapi_fallback(text: str) -> str:
    """
    Offline fallback using Windows native SAPI (Speech Synthesizer) via PowerShell.
    Returns path to compiled wav file.
    """
    temp_dir = tempfile.gettempdir()
    out_path = os.path.join(temp_dir, f"arch_tts_fallback_{os.urandom(4).hex()}.wav")
    
    # Escape single quotes and newlines for PowerShell
    safe_text = text.replace("'", "''").replace("\n", " ").strip()
    
    # PowerShell commands to output synthesis to file
    ps_script = (
        "Add-Type -AssemblyName System.Speech; "
        "$synth = New-Object System.Speech.Synthesis.SpeechSynthesizer; "
        "$synth.Rate = -1; " # Slightly faster
        f"$synth.SetOutputToWaveFile('{out_path}'); "
        f"$synth.Speak('{safe_text}'); "
        "$synth.Dispose();"
    )
    
    try:
        print("[TTS] Synthesizing speech using Windows SAPI fallback...")
        subprocess.run(
            ["powershell", "-NoProfile", "-ExecutionPolicy", "Bypass", "-Command", ps_script],
            capture_output=True,
            text=True,
            check=True
        )
        if os.path.exists(out_path) and os.path.getsize(out_path) > 0:
            return out_path
    except Exception as e:
        print(f"[TTS] SAPI fallback failed: {e}")
        
    return ""

def synthesize_speech(text: str) -> str:
    """
    Main entry point. Synthesizes text to audio.
    Returns path of generated wav file.
    """
    cleaned_text = clean_markdown_for_speech(text)
    if not cleaned_text:
        return ""
        
    lang = detect_language(cleaned_text)
    
    # Try Piper first
    try:
        voice = get_piper_voice(lang)
        temp_dir = tempfile.gettempdir()
        out_path = os.path.join(temp_dir, f"arch_tts_{os.urandom(4).hex()}.wav")
        
        print(f"[TTS] Synthesizing '{cleaned_text[:60]}...' using Piper ({lang})")
        with wave.open(out_path, "wb") as wav_file:
            voice.synthesize_wav(cleaned_text, wav_file)
            
        if os.path.exists(out_path) and os.path.getsize(out_path) > 0:
            return out_path
    except Exception as e:
        print(f"[TTS] Piper synthesis failed/unavailable: {e}. Falling back to SAPI...")
        
    # Fallback to SAPI
    return synthesize_sapi_fallback(cleaned_text)
