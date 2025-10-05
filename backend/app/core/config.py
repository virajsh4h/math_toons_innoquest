# config
import os
from dotenv import load_dotenv

# Load environment variables from the .env file in the `backend` directory
dotenv_path = os.path.join(os.path.dirname(__file__), '..', '..', '.env')
load_dotenv(dotenv_path=dotenv_path)

class Settings:
    GEMINI_API_KEY: str = os.getenv("GEMINI_API_KEY")
    CUSTOM_TTS_API_URL: str = os.getenv("CUSTOM_TTS_API_URL")
    R2_ENDPOINT_URL: str = os.getenv("R2_ENDPOINT_URL")
    R2_ACCESS_KEY_ID: str = os.getenv("R2_ACCESS_KEY_ID")
    R2_SECRET_ACCESS_KEY: str = os.getenv("R2_SECRET_ACCESS_KEY")
    R2_BUCKET_NAME: str = os.getenv("R2_BUCKET_NAME")
    ELEVENLABS_API_KEY: str = os.getenv("ELEVENLABS_API_KEY")
    R2_PUBLIC_URL_BASE: str = os.getenv("R2_PUBLIC_URL_BASE") 


    # print(GEMINI_API_KEY)
    # print(CUSTOM_TTS_API_URL)
    print(ELEVENLABS_API_KEY)
    print(R2_ENDPOINT_URL)
    print(R2_ACCESS_KEY_ID)
    print(R2_SECRET_ACCESS_KEY)
    print(R2_BUCKET_NAME)

settings = Settings()