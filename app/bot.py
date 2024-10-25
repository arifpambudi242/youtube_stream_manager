import os
import signal
import subprocess
import time

def stream_to_youtube(video_path, stream_key, repeat=True):
    video_path = f'app/static/{video_path}'.replace('\\', '/')
    youtube_rtmp_url = f'rtmp://a.rtmp.youtube.com/live2/{stream_key}'  # Ganti stream_key sesuai kebutuhan
    
    command = [
        'ffmpeg',
        '-re',  # Membaca input sesuai kecepatan frame asli
        '-i', video_path,  # Jalur video input
        '-c:v', 'libx264',  # Codec video
        '-preset', 'veryfast',  # Kecepatan encoding
        '-maxrate', '3000k',  # Bitrate maksimal
        '-bufsize', '6000k',  # Ukuran buffer
        '-pix_fmt', 'yuv420p',  # Format pixel
        '-g', '50',  # Ukuran grup gambar (keyframe)
        '-c:a', 'aac',  # Codec audio
        '-b:a', '160k',  # Bitrate audio
        '-f', 'flv',  # Format output RTMP
        youtube_rtmp_url  # URL RTMP tujuan streaming
    ]

    if repeat:
        command.insert(1, '-stream_loop')
        command.insert(2, '-1')

    process = subprocess.Popen(command)
    return process

def stop_stream_by_pid(pid):
    try:
        os.kill(pid, signal.SIGTERM)
    except OSError as e:
        raise e

def is_stream_started(process):
    return process is not None

def is_stream_alive(pid):
    try:
        os.kill(pid, 0)  # Send signal 0 to check if the process is alive
    except OSError:
        return False
    return True

def start_stream_youtube(video_path, stream_key, delay=0, repeat=True):
    if delay > 0:
        time.sleep(delay)
    
    process = stream_to_youtube(video_path, stream_key, repeat)
    return process.pid