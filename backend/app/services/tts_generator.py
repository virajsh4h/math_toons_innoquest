# backend/app/services/tts_generator.py
import os
import uuid
import asyncio
from elevenlabs import save
from elevenlabs.client import ElevenLabs
from app.core.config import settings
import ffmpeg # We keep this for the 15% slowdown/speedup (15% slower = 0.85 atempo)

TEMP_ASSETS_DIR = "/tmp/math_toons_assets"
os.makedirs(TEMP_ASSETS_DIR, exist_ok=True)

client = ElevenLabs(api_key=settings.ELEVENLABS_API_KEY)

# ElevenLabs voice map for multilingual
# The 'Dora' voice is excellent for multilingual and sounds like a child host.
VOICE_MAP = {
    "en": "pFZP5JQG7iQjIQuC4Bku", # Use a multilingual voice ID
    "hi": "pFZP5JQG7iQjIQuC4Bku",
    "mr": "pFZP5JQG7iQjIQuC4Bku",
    # You can map different voices here if needed, but Dora is a safe, multilingual choice
}

def _speed_adjust_audio(input_path: str, output_path: str, speed_factor: float):
    """
    Synchronous function to speed adjust (slow down) an MP3 file using ffmpeg's atempo filter.
    0.85 factor makes the audio 15% slower (1 / 1.15 = 0.869... but 0.85 is a safe, noticeable change).
    """
    try:
        temp_output_path = f"{output_path}.temp.mp3"
        
        (
            ffmpeg
            .input(input_path)
            .filter('atempo', speed_factor) # Use speed_factor (0.85 for 15% slower)
            .output(temp_output_path, acodec='libmp3lame')
            .run(overwrite_output=True, quiet=True)
        )
        os.replace(temp_output_path, output_path)
        print(f"  [TTS-FFmpeg] Successfully adjusted audio speed by factor {speed_factor}: {output_path}")
        
    except ffmpeg.Error as e:
        print(f"  [TTS-FFmpeg] Error adjusting audio speed: {e.stderr.decode('utf8')}")
        if os.path.exists(temp_output_path):
            os.remove(temp_output_path)
        raise

def _blocking_elevenlabs_tts(narration: str, final_output_path: str, lang: str):
    """
    Synchronous function for ElevenLabs API call and file saving with language support.
    """
    voice_name = VOICE_MAP.get(lang, VOICE_MAP["en"])
    
    # 1. Generate the raw audio to a temp file
    temp_raw_audio_path = f"{final_output_path}.raw.mp3"
    
    audio_stream = client.text_to_speech.convert(
        text=narration,
        voice_id=voice_name,
        # eleven_multilingual_v2 is the best for Hindi/Marathi/English
        # model_id="eleven_multilingual_v2", 
        model_id="eleven_turbo_v2_5", 
        output_format="mp3_44100_128" 
    )
    
    save(audio_stream, temp_raw_audio_path)
    
    # 2. Slow down the audio (15% slower = 0.85 factor) and save it to the final path
    _speed_adjust_audio(temp_raw_audio_path, final_output_path, speed_factor=0.90)

    # hiiii lets checkkkkkk
    
    # 3. Clean up the raw temp file
    os.remove(temp_raw_audio_path)
    
    return final_output_path

async def generate_tts_audio(narration: str, character: str, output_dir: str, lang: str) -> str: # <-- ADDED lang
    """
    Asynchronously generates high-quality TTS audio and then slows it down.
    """
    print(f"  [TTS-ElevenLabs] Generating audio...")
    
    audio_filename = f"scene_audio_{uuid.uuid4().hex[:8]}.mp3"
    output_path = os.path.join(output_dir, audio_filename)
    
    loop = asyncio.get_running_loop()
    
    try:
        # Pass the language code to the blocking function
        await loop.run_in_executor(
            None, _blocking_elevenlabs_tts, narration, output_path, lang
        )
        
        if not os.path.exists(output_path) or os.path.getsize(output_path) == 0:
            raise FileNotFoundError("ElevenLabs TTS failed to create a valid audio file.")

        print(f"  [TTS-ElevenLabs] Successfully generated and speed-adjusted audio: {output_path}")
        return output_path

    except Exception as e:
        print(f"  [TTS-ElevenLabs] Failed to generate audio. Error: {e}")
        raise