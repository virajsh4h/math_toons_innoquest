# lets use gemini 2.0 flash for api calls because its smart and fast lfg

import google.generativeai as genai
from .config import settings

# Configure the Gemini API client
genai.configure(api_key=settings.GEMINI_API_KEY)

# Initialize the model
model = genai.GenerativeModel('gemini-2.5-flash-lite')

print("Gemini model initialized successfully.")