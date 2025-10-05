# backend/app/services/video_stitcher.py
import os
import uuid
import ffmpeg
from moviepy import VideoFileClip, AudioFileClip, concatenate_videoclips
import random # <-- NEW IMPORT

def get_stream_duration(stream_path: str, stream_type: str) -> float:
    """Get the duration of a specific stream type from a file using ffprobe."""
    try:
        # NOTE: moviepy's AudioFileClip is more resilient for formats like MP3/AIFF/WAV
        # We will use that for duration calculation to avoid edge cases.
        if stream_type == 'audio':
            clip = AudioFileClip(stream_path)
            duration = clip.duration
            clip.close()
            return duration
            
        probe = ffmpeg.probe(stream_path)
        video_stream = next((s for s in probe['streams'] if s['codec_type'] == stream_type), None)
        return float(video_stream['duration'])
    except Exception as e:
        print(f"  [Stitcher-FFmpeg] Error getting {stream_type} duration for {stream_path}: {e}")
        return 0

def combine_scene_assets(video_path: str, audio_path: str, output_dir: str) -> str:
    """Combines video and audio using ffmpeg-python. This is ROCK SOLID."""
    print(f"  [Stitcher-FFmpeg] Combining scene: {os.path.basename(video_path)} + {os.path.basename(audio_path)}")
    output_filename = f"combined_scene_{uuid.uuid4().hex[:8]}.mp4"
    output_path = os.path.join(output_dir, output_filename)

    try:
        video_duration = get_stream_duration(video_path, 'video')
        audio_duration = get_stream_duration(audio_path, 'audio')

        video_input = ffmpeg.input(video_path)
        audio_input = ffmpeg.input(audio_path)

        if audio_duration > video_duration:
            video_input = video_input.filter('tpad', stop_mode='clone', stop_duration=(audio_duration - video_duration))

        (
            ffmpeg
            .output(video_input, audio_input, output_path, vcodec='libx264', acodec='aac', shortest=None, t=audio_duration)
            .run(quiet=True, overwrite_output=True)
        )
        
        print(f"  [Stitcher-FFmpeg] Scene combined successfully: {output_path}")
        return output_path

    except Exception as e:
        print(f"  [Stitcher-FFmpeg] Error combining scene assets: {e}")
        raise

def stitch_final_video(scene_paths: list, output_dir: str) -> str:
    """Concatenates scenes and then uses ffmpeg to add background music."""
    if not scene_paths:
        raise ValueError("Cannot stitch video, no scene paths provided.")
        
    print(f"  [Stitcher] Stitching {len(scene_paths)} scenes into final video...")
    
    intermediate_video_path = os.path.join(output_dir, f"intermediate_{uuid.uuid4().hex[:8]}.mp4")
    output_path = os.path.join(output_dir, "final_video.mp4")
    
    clips = [VideoFileClip(path) for path in scene_paths]
    final_clip = concatenate_videoclips(clips, method="compose")
    
    final_clip.write_videofile(intermediate_video_path, codec="libx264", audio_codec="aac", logger=None)
    
    for clip in clips:
        clip.close()
    final_clip.close()

    # --- UPDATED MUSIC LOGIC ---
    music_options = ["assets/music/mu1.mp3", "assets/music/mu2.mp3"]
    music_path = random.choice(music_options)

    if os.path.exists(music_path):
        print(f"  [Stitcher-FFmpeg] Adding background music from {os.path.basename(music_path)} with ffmpeg...")
        try:
            video_input = ffmpeg.input(intermediate_video_path)
            music_input = ffmpeg.input(music_path)

            main_audio = video_input.audio
            bg_music = music_input.audio

            # CRITICAL FIX: Reduce volume to 0.15
            bg_music = bg_music.filter('volume', 0.22)
            mixed_audio = ffmpeg.filter([main_audio, bg_music], 'amix', duration='first', dropout_transition=1)

            (
                ffmpeg
                .output(video_input['v'], mixed_audio, output_path, vcodec='copy', acodec='aac')
                .run(quiet=True, overwrite_output=True)
            )
            os.remove(intermediate_video_path)
            
            print(f"  [Stitcher-FFmpeg] Background music added successfully: {output_path}")
        except Exception as e:
            print(f"  [Stitcher-FFmpeg] Error adding background music: {e}")
            os.rename(intermediate_video_path, output_path)
    else:
        print(f"  [Stitcher-FFmpeg] WARNING: Background music file not found at {music_path}. Skipping background music.")
        os.rename(intermediate_video_path, output_path)
    
    print(f"--- ✅ ✅ ✅ Backend Complete! ✅ ✅ ✅ ---")
    print(f"  [Stitcher] Final video stitched successfully at: {output_path}")
    return output_path