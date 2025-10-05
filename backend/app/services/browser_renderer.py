import asyncio
import os
import uuid
import json
import base64
from playwright.async_api import async_playwright

# The absolute path to your frontend directory
FRONTEND_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..', '..', 'frontend'))
INDEX_HTML_PATH = os.path.join(FRONTEND_DIR, 'index.html')

async def render_scene_with_browser(animation_data: dict, output_dir: str) -> str:
    """
    Renders a scene by controlling a headless browser with Playwright.
    """
    scene_id = f"scene_{uuid.uuid4().hex[:8]}"
    output_path = os.path.join(output_dir, f"{scene_id}.mp4")

    print(f"  [Browser] Starting render for scene {scene_id}")

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        # Use a new context to enable video recording
        context = await browser.new_context(
            viewport={'width': 1280, 'height': 720},
            record_video_dir=output_dir,
            record_video_size={'width': 1280, 'height': 720}
        )
        
        page = await context.new_page()

        # Listen for the 'PAGE_READY' and 'ANIMATION_COMPLETE' signals
        page_ready_event = asyncio.Event()
        animation_complete_event = asyncio.Event()

        def handle_console(msg):
            if "---PAGE_READY---" in msg.text:
                page_ready_event.set()
            elif "---ANIMATION_COMPLETE---" in msg.text:
                animation_complete_event.set()
        
        page.on('console', handle_console)

        # Navigate to the local HTML file
        await page.goto(f"file://{INDEX_HTML_PATH}")

        # Wait for the page and PixiJS to be fully ready
        await page_ready_event.wait()
        print(f"  [Browser] Page is ready for scene {scene_id}")

        # Execute the animation function in the browser's context
        await page.evaluate(f"window.runAnimation({json.dumps(animation_data)})")

        # Wait for the animation to signal its completion
        await animation_complete_event.wait()
        print(f"  [Browser] Animation complete for scene {scene_id}")

        # Close the context to save the video
        await context.close()
        await browser.close()
        
        # Playwright saves with a random name, we need to find and rename it
        video_files = [f for f in os.listdir(output_dir) if f.endswith('.webm')]
        if video_files:
            os.rename(os.path.join(output_dir, video_files[0]), output_path)
            print(f"  [Browser] Scene rendered successfully: {output_path}")
            return output_path
        else:
            raise Exception("Playwright did not save a video file.")