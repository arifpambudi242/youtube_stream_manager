import os
import signal
import subprocess
import time
import ffmpeg
import psutil

def stream_to_youtube(video_path, stream_key, repeat=True):
    video_path = f'app/static/{video_path}'.replace('\\', '/')
    youtube_rtmp_url = f'rtmp://a.rtmp.youtube.com/live2/{stream_key}'  # Customize stream_key as needed
    
    print(f'Streaming {video_path} to {youtube_rtmp_url}{" in loop" if repeat else ""}...')

    # Construct the ffmpeg-python command
    stream = (
        ffmpeg
        .input(video_path, stream_loop=-1 if repeat else None, re=True)  # Set looping and reading rate
        .output(
            youtube_rtmp_url,
            c_v='libx264',         # Video codec
            preset='veryfast',     # Encoding speed
            maxrate='3000k',       # Maximum bitrate
            bufsize='6000k',       # Buffer size
            pix_fmt='yuv420p',     # Pixel format
            g=50,                  # Group of pictures size (keyframe interval)
            c_a='aac',             # Audio codec
            b_a='160k',            # Audio bitrate
            f='flv'                # Output format for RTMP
        )
        .global_args('-y')  # Overwrite output files without asking
    )

    # Run the process asynchronously to allow interaction
    process = stream.run_async(pipe_stdout=True, pipe_stderr=True, pipe_stdin=True)
    return process
    

# List all running ffmpeg processes
def list_ffmpeg_processes():
    ffmpeg_processes = []
    for process in psutil.process_iter(['pid', 'name', 'cmdline']):
        try:
            if 'ffmpeg' in process.info['name'] or 'ffmpeg' in (process.info['cmdline'] or []):
                ffmpeg_processes.append(process)
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            continue
    return ffmpeg_processes

def stop_stream_by_pid(pid):
    try:
        ffmpeg = psutil.Process(pid)
        ffmpeg.terminate()
    except psutil.NoSuchProcess:
        return False
    try:
        ffmpeg.wait(timeout=1)
    except psutil.TimeoutExpired:
        ffmpeg.kill()
    return True

def is_stream_started(pid):
    try:
        ffmpeg = psutil.Process(pid)
    except psutil.NoSuchProcess:
        return False
    return ffmpeg.is_running()

def is_stream_alive(pid):
    try:
        os.kill(pid, 0)  # Send signal 0 to check if the process is alive
    except OSError:
        return False
    return True

def start_stream_youtube(video_path, stream_key, repeat=True):
    process = stream_to_youtube(video_path, stream_key, repeat)
    return process.pid