import os
from dotenv import load_dotenv
from elevenlabs.client import ElevenLabs

# Load the .env file from the backend directory
load_dotenv()
#EXAVITQu4vr4xnSDxMaL
print("--- Checking for available ElevenLabs voices ---")

api_key = os.getenv("ELEVENLABS_API_KEY")
if not api_key:
    print("!!! ERROR: ELEVENLABS_API_KEY not found in your .env file.")
else:
    try:
        client = ElevenLabs(api_key=api_key)
        
        voices = client.voices.get_all()
        
        if not voices.voices:
            print("No voices found for your account.")
        else:
            print("✅ Success! Found the following voices available on your free tier:")
            for voice in voices.voices:
                print(f"- Name: {voice.name}, Voice ID: {voice.voice_id}")

    except Exception as e:
        print(f"!!! An error occurred while fetching voices: {e}")

print("--- Check complete ---")