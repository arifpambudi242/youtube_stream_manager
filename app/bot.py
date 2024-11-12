import os
import signal
import subprocess
import time
import ffmpeg
import psutil

def stream_to_youtube(video_path, stream_key, repeat=True):
    video_path = f'app/static/{video_path}'.replace('\\', '/')
    youtube_rtmp_url = f'rtmp://a.rtmp.youtube.com/live2/{stream_key}'  # Ganti stream_key sesuai kebutuhan
    print(f'Streaming {video_path} to {youtube_rtmp_url}{" in loop" if repeat else ""}...')

    # Sesuaikan bitrate, ukuran grup gambar, dan buffer untuk performa streaming yang lebih baik
    command = [
        'ffmpeg',
        '-i', f"{video_path}",  # Jalur video input
        '-c:v', 'libx264',  # Codec video
        '-b:v', '5000k',  # Meningkatkan bitrate video untuk kualitas yang lebih baik
        '-maxrate', '6000k',  # Bitrate maksimal untuk menghindari fluktuasi besar
        '-bufsize', '8000k',  # Ukuran buffer yang lebih besar untuk stabilitas
        '-pix_fmt', 'yuv420p',  # Format pixel
        '-g', '60',  # Interval keyframe lebih besar (setiap 2 detik untuk 30fps)
        '-c:a', 'aac',  # Codec audio
        '-b:a', '192k',  # Bitrate audio yang lebih tinggi untuk kualitas suara lebih baik
        '-f', 'flv',  # Format output RTMP
        youtube_rtmp_url  # URL RTMP tujuan streaming
    ]

    if repeat:
        command.insert(1, '-stream_loop')
        command.insert(2, '-1')

    # Menjalankan perintah FFmpeg dalam mode background dengan menangkap output error
    process = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, stdin=subprocess.PIPE, shell=False)
    
    # Memeriksa error jika ada
    stdout, stderr = process.communicate()
    if stderr:
        print(f"Error during streaming: {stderr.decode()}")
    else:
        print(f"Streaming process started successfully.")

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