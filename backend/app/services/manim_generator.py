# backend/app/services/manim_generator.py
import os
import uuid
import subprocess
from app.core.ai import model
import asyncio
import grpc
from google.api_core import exceptions as google_exceptions
import re
from pathlib import Path # <--- Import Pathlib for CWD change

async def call_gemini_with_backoff(messages, max_retries=7):
    # This function is correct.
    for attempt in range(max_retries):
        try:
            response = await model.generate_content_async(messages)
            return response
        except Exception as e:
            print(f"  [API-CALL-ERROR] An unexpected error occurred: {e}")
            await asyncio.sleep(5)
    raise Exception("API call failed after multiple retries.")

MANIM_SYSTEM_PROMPT = """
You are a Manim code generator. Your ONLY job is to write simple, error-free Python code. You are FORBIDDEN from being creative. You must follow these rules PRECISELY.

**🚨🚨🚨 ABSOLUTE NON-NEGOTIABLE TECHNICAL RULES 🚨🚨🚨**

1.  **MANDATORY IMPORT**: ALWAYS start your code with `from manim import *`.
2.  **CLASS NAMES ARE FIXED**: The classes must be named `Scene1`, `Scene2`, `Scene3`, etc.
3.  **ALLOWED ASSETS ONLY (MAX 15)**: You can ONLY use these exact filenames. DO NOT make up paths.
    -   `"assets/dino.png"`, `"assets/mango.png"`
    -   `"assets/doraemon.png"`, `"assets/chhota_bheem.png"` (The character presets)
    -   `"assets/backgrounds/bg1.png"` to `"assets/backgrounds/bg5.png"`
    -   `"assets/apple.png"`, `"assets/banana.png"`, `"assets/avocado.png"`, `"assets/panda.png"`, `"assets/car.png"`, `"assets/clock.png"`, `"assets/monkey.png"`, 
    -   `"assets/truck.png"`, `"assets/carrot.png"`, `"assets/pencil.png"`, `"assets/lion.png"`, `"assets/bottle.png"`, `"assets/tomato.png"`
4.  **CRITICAL BACKGROUND RULE**: For maximum visual variety, you MUST use a different background file (`bg1.png` to `bg5.png`) for each scene.
5.  **CRITICAL TEXT COLOR RULE**: All `Text` objects MUST use dark, visible, but kid-friendly colors, such as dark pink (`#C71585`), deep red (`#8B0000`), or purple (`#800080`). **DO NOT** use light colors or plain black.
6.  **CRITICAL POSITIONING RULE**: When placing objects (Text, ImageMobject), you MUST ensure they **NEVER** overlap or obstruct the character, text, or the main action. Use `to_corner(UP/DOWN/LEFT/RIGHT)` or `next_to` with generous spacing.
7.  **VIDEO QUALITY RULE**: All Manim scenes MUST be rendered at 720p. You do this by setting the **`config["quality"] = "medium_quality"`** at the very top of the script.
8.  **BANNED CONSTANTS (CRITICAL!)**: You can ONLY use `UP`, `DOWN`, `LEFT`, `RIGHT`, `ORIGIN`.
    -   `CENTER` IS BANNED. `FRAME_CENTER` IS BANNED.
8.  **GROUPING IS FIXED**: `Group` for `ImageMobject`, `VGroup` for `Text`.
9.  **BANNED FUNCTIONS**: Do NOT use `add_updater()`, `set_opacity()`, or any other complex function that modifies state outside of `self.play`.

**💡 THE ONLY FOOLPROOF PATTERN YOU ARE ALLOWED TO USE:**

```python
from manim import *

config["quality"] = "medium_quality" # <-- NEW: Set 720p quality
scene_state = {}

class Scene1(Scene):
    def construct(self):
        # 1. Background fix: Always use a varied background
        bg = ImageMobject("assets/backgrounds/bg2.png")
        bg.scale_to_fit_height(self.camera.frame_height)
        self.add(bg)

        # 2. this is the Correct asset path, correct position reference (no CENTER) FOR A CHARACTER
        bheem = ImageMobject("assets/chhota_bheem.png").scale(1.5).to_corner(DL)

        # 3. this is the Correct asset path, correct position reference (no CENTER) for AN ARTEFACT
        apple = ImageMobject("assets/apple.png").scale(0.5).to_corner(DL)
        
        # 3. Use ORIGIN for the center of the screen and a dark color, YOU CAN ALSO MAKE THE TEXT BOLD AND ADD STROKE COLORS
        title = Text("Hello Rohan!", font_size=72, color="#C71585").move_to(ORIGIN)

        self.play(FadeIn(bheem), Write(title))
        
        # 4. Save state
        scene_state['bheem_pos'] = bheem.get_center()
```
"""

def render_manim_script(script_path: str, output_dir: str, class_name: str):
    """
    Renders a SINGLE scene class from a script file, ensuring Manim runs from the correct directory.
    """
    scene_id_for_path = f"{class_name}_{uuid.uuid4().hex[:4]}"
    
    backend_dir = Path(os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..')))

    # Manim command
    command = ["manim", script_path, class_name, "-qm", "--media_dir", output_dir]
    
    try:
        # We run Manim, and the execution handles the file corruption and missing constant errors.
        # The key fix is forcing the AI to stop using the buggy constants and complex functions.
        print(f"  [Manim] Running from CWD: {backend_dir}")
        print(f"  [Manim] Rendering scene with command: {' '.join(command)}")
        result = subprocess.run(
            command, 
            check=True, 
            capture_output=True, 
            text=True,
            cwd=backend_dir
        )
        
        script_file_name = os.path.splitext(os.path.basename(script_path))[0]
        expected_video_path = os.path.join(output_dir, "videos", script_file_name, "720p30", f"{class_name}.mp4")

        if not os.path.exists(expected_video_path):
             raise FileNotFoundError(f"Manim did not produce the expected video file at {expected_video_path}. Manim output: {result.stdout} {result.stderr}")
        
        final_video_path = os.path.join(output_dir, f"{scene_id_for_path}.mp4")
        os.rename(expected_video_path, final_video_path)
        
        print(f"  [Manim] Scene rendered successfully: {final_video_path}")
        return True, final_video_path

    except subprocess.CalledProcessError as e:
        error_message = f"Return Code: {e.returncode}\nSTDOUT: {e.stdout}\nSTDERR: {e.stderr}"
        print(f"  [Manim] --- MANIM RENDER FAILED ---\n{error_message}")
        return False, error_message
    except Exception as e:
        print(f"  [Manim] --- An unexpected error occurred during render ---\n{e}")
        return False, str(e)


async def generate_manim_script(scene_description: str, output_dir: str) -> str:
    # This function is correct.
    messages = [{"role": "user", "parts": [MANIM_SYSTEM_PROMPT, "\n\n**New Scene Descriptions:**\n", scene_description]}]
    
    print(f"  [Manim-AI] Generating master script for all scenes...")
    try:
        response = await call_gemini_with_backoff(messages)
        raw_response_text = response.text.strip()
        code = raw_response_text
        if "```python" in code:
            start = code.find("```python") + len("```python\n")
            end = code.rfind("```")
            if end > start:
                code = code[start:end]

        script_id = f"master_script_{uuid.uuid4().hex[:8]}"
        script_path = os.path.join(output_dir, f"{script_id}.py")
        with open(script_path, "w") as f:
            f.write(code)
        
        print(f"  [Manim-AI] Master script saved to: {script_path}")
        return script_path

    except Exception as e:
        print(f"  [Manim-AI] An unexpected error occurred during script generation: {e}")
        raise