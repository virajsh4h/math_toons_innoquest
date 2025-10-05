# backend/app/services/video_generator.py
import json
import os
import uuid
import asyncio
import shutil
from app.models.video import VideoGenerationRequest
from app.core.ai import model
from app.core.config import settings
from app.services.tts_generator import generate_tts_audio, TEMP_ASSETS_DIR
from app.services.manim_generator import generate_manim_script, render_manim_script
from app.services.video_stitcher import combine_scene_assets, stitch_final_video
from app.services.storage_service import upload_video_to_r2 
from asyncio import Semaphore

# --- THE FINAL, "SHUT UP AND DO YOUR JOB" PROMPT (Manim Version) ---
def create_storyboard_prompt(request: VideoGenerationRequest) -> str:
    """
    This is a brutally direct prompt that gives the AI zero room for creative replies.
    It now requests a simple 'scene_description' for Manim.
    """
    artifacts_str = ', '.join(request.artifacts)
    character = request.character_preset
    student_name = request.student_name
    topic = request.topic

    # This prompt is intentionally rude and robotic.
    prompt = f"""
        You are a JSON data generation bot. Your ONLY task is to take the following details and convert them into a valid JSON object.

        **DETAILS:**
        - Student Name: {student_name}
        - Topic: "{topic}"
        - Artifacts: {artifacts_str}
        - Host: {character}
        - Target Language: {request.lang}

        **RULES:**
        1.  YOU MUST OUTPUT A SINGLE, VALID JSON OBJECT AND NOTHING ELSE.
        2.  The JSON object must have a single key "storyboard", which is a list of scene objects.
        3.  **CRITICAL DURATION RULE**: To ensure the final video is a MINIMUM of 120 seconds (2 minutes) to a MAXIMUM of 180 seconds (3 minutes), you MUST generate a MINIMUM of 15 scenes and a MAXIMUM of 30 scenes.
        4.  **CRITICAL COHERENCE RULE**: The scenes MUST follow a clear, coherent but engaging high quality narrative  as if the narrator is the {character}. Eg: (Introduction -> Problem Setup -> Step 1 -> Step 2 -> Solution -> Explanation -> Practice Question -> Solution -> Conclusion) that smoothly explains the math topic. Each new scene must logically advance the story from the previous one.
        5.  CRITICAL PAUSING RULE: The narration MUST use three consecutive periods (`...`) to indicate a short, child-friendly pause, and MUST aim for 5-10 seconds of descriptive speech per scene.
        6.  CRITICAL LANGUAGE RULE: If the request language is 'hi' (Hindi) or 'mr' (Marathi), the entire `narration` MUST be written in the **Devanagari script**. If the language is 'en', use English.
        7.  The "scene_description" MUST be simple visual instructions for a Manim scene (these remain in English).
        8.  DO NOT write any introductory text, explanations, or conversational replies like "Okay, I'm ready!". Your entire response must be ONLY the JSON.

        **JSON SCHEMA EXAMPLE (Hindi/Devanagari):**
        {{
        "storyboard": [
            {{
            "scene_number": 1,
            "scene_description": "The host character, {character}, is in the bottom-left corner, waving. The student's name, '{student_name}!', appears in the center in big, colorful, bouncy letters. Use background bg1.png.",
            "narration": "नमस्ते {student_name}... मैं {character} हूँ। क्या तुम आज हमारे साथ गणित के मज़ेदार सफ़र के लिए तैयार हो?"
            }}
        ]
        }}

        GENERATE THE JSON NOW.
        """
    return prompt


async def generate_video_storyboard(request: VideoGenerationRequest) -> list:
    """Uses the Gemini model to generate a storyboard, now with robust error checking."""
    prompt = create_storyboard_prompt(request)
    try:
        print("  [Orchestrator] Sending prompt to Gemini API for storyboard...")
        
        # NOTE: The rest of the function (response parsing) remains the same.
        response = await model.generate_content_async(
            prompt,
            safety_settings={'HARM_CATEGORY_HARASSMENT': 'BLOCK_NONE',
                             'HARM_CATEGORY_HATE_SPEECH': 'BLOCK_NONE',
                             'HARM_CATEGORY_SEXUALLY_EXPLICIT': 'BLOCK_NONE',
                             'HARM_CATEGORY_DANGEROUS_CONTENT': 'BLOCK_NONE'}
        )
        
        if not response.parts:
            print("  [Orchestrator] !!! CRITICAL ERROR: Gemini API returned an empty response.")
            print(f"  [Orchestrator] Prompt Feedback: {response.prompt_feedback}")
            raise ValueError("Storyboard generation failed: The API returned an empty response, likely due to safety filters.")

        response_text = response.text.strip().replace("```json", "").replace("```", "").strip()
        
        print("  [Orchestrator] Received storyboard from Gemini API.")

        if not response_text:
             raise ValueError("Storyboard generation failed: The API returned text but it was empty after cleaning.")

        storyboard_data = json.loads(response_text)
        return storyboard_data.get("storyboard", [])
    except json.JSONDecodeError as e:
        print(f"  [Orchestrator] !!! CRITICAL JSON DECODE ERROR: The AI did not return valid JSON.")
        print(f"  [Orchestrator] The invalid text from the API was: {response.text}")
        raise ValueError(f"Failed to decode JSON from AI. Invalid text: {response.text}")
    except Exception as e:
        print(f"  [Orchestrator] An error occurred while generating storyboard: {e}")
        raise

async def create_personalized_video(request: VideoGenerationRequest):
    task_id = uuid.uuid4().hex
    output_dir = os.path.join(TEMP_ASSETS_DIR, task_id)
    os.makedirs(output_dir, exist_ok=True)
    
    print(f"[Orchestrator] Starting video generation task {task_id} for {request.student_name}")
    
    final_video_path = None
    final_video_url = None
    
    try:
        storyboard = await generate_video_storyboard(request)
        if not storyboard:
            raise ValueError("Storyboard generation failed or returned empty.")

        full_scene_description = "\n\n".join([f"**Scene {s['scene_number']} Description:**\n{s['scene_description']}" for s in storyboard])
        master_script_path = await generate_manim_script(full_scene_description, output_dir)
        
        successful_assets = []
        concurrency_limit = 1 
        semaphore = Semaphore(concurrency_limit)
        
        async def render_and_tts_for_scene(scene_data):
            async with semaphore:
                scene_num = scene_data['scene_number']
                class_name = f"Scene{scene_num}"
                print(f"  [Orchestrator] Processing Scene {scene_num} ({class_name})")
                
                loop = asyncio.get_running_loop()
                
                render_task = loop.run_in_executor(
                    None, render_manim_script, master_script_path, output_dir, class_name
                )
                
                # We need to pass the language ('lang') from the request to the TTS generator
                tts_task = generate_tts_audio(
                    scene_data['narration'], 
                    request.character_preset, 
                    output_dir, 
                    request.lang 
                ) 
                
                render_result, audio_path = await asyncio.gather(render_task, tts_task, return_exceptions=False)
                
                render_success, video_path_or_error = render_result

                if not render_success:
                    raise Exception(f"Failed to render scene {scene_num}: {video_path_or_error}")
                
                return video_path_or_error, audio_path

        tasks = [render_and_tts_for_scene(scene) for scene in storyboard]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        for i, result in enumerate(results):
            if isinstance(result, Exception):
                print(f"  [Orchestrator] !!! WARNING: Scene {i+1} failed to process and will be SKIPPED. Error: {result}")
            else:
                successful_assets.append(result)
        
        if not successful_assets:
            raise Exception("All scenes failed to generate. No video can be created.")

        print(f"  [Orchestrator] {len(successful_assets)}/{len(storyboard)} scenes generated successfully.")

        loop = asyncio.get_running_loop()
        combined_scene_paths = []
        for video_path, audio_path in successful_assets:
            combined_path = await loop.run_in_executor(
                None, combine_scene_assets, video_path, audio_path, output_dir
            )
            if combined_path:
                combined_scene_paths.append(combined_path)

        if not combined_scene_paths:
             raise Exception("All scenes failed to combine. No video can be created.")

        final_video_path = await loop.run_in_executor(
            None, stitch_final_video, combined_scene_paths, output_dir
        )
        
        # --- NEW: Upload to R2 and get public URL ---
        video_key = f"{request.student_name.lower().replace(' ', '_')}/{task_id}.mp4"
        
        uploaded_key = await upload_video_to_r2(final_video_path, video_key)
        # CRITICAL FIX: Assemble the final public URL
        if settings.R2_PUBLIC_URL_BASE:
            final_video_url = f"{settings.R2_PUBLIC_URL_BASE.rstrip('/')}/{uploaded_key}"
        else:
            final_video_url = f"R2 Upload Successful: Missing R2_PUBLIC_URL_BASE to create final link. Key: {uploaded_key}"
            
        print(f"--- ✅ ✅ ✅ SUCCESS! ✅ ✅ ✅ ---")
        print(f"  [Orchestrator] Final video created and uploaded. Public URL: {final_video_url}")
        
        return final_video_url 
        
    except Exception as e:
        print(f"  [Orchestrator] A critical error occurred during video generation: {e}")
        return None # Return None on failure
    finally:
        # shutil.rmtree(output_dir, ignore_errors=True)
        pass