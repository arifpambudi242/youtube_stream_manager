import os
import signal
import subprocess
import threading

class CustomThread(threading.Thread):
    def __init__(self, video_path, stream_key):
        threading.Thread.__init__(self)
        self.video_path = f'app/static/{video_path}'
        self.stream_key = stream_key
        self.repeat = True
        self.process = None

    def stream_to_youtube(self):
        # Konfigurasi jalur video dan URL RTMP YouTube
        video_path = self.video_path.replace('\\', '/')
        youtube_rtmp_url = f'rtmp://a.rtmp.youtube.com/live2/{self.stream_key}'  # Ganti stream_key sesuai kebutuhan
        
        # Command dasar untuk streaming ke YouTube
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

        # Mengulangi video jika opsi repeat aktif
        if self.repeat:
            command.insert(1, '-stream_loop')
            command.insert(2, '-1')

        # Menjalankan proses ffmpeg dan menyimpan ID proses
        self.process = subprocess.Popen(command)
        self.process_id = self.process.pid  # Simpan PID untuk referensi
        return self.process_id
        
    def start(self):
        # Mulai streaming ke YouTube
        return self.stream_to_youtube()
        
    def stop(self):
        if self.process:
            try:
                # Stop the process specifically using PID
                os.kill(self.process.pid, signal.SIGTERM)  # Send terminate signal to the process
                self.process.wait()  # Wait for the process to terminate
            except OSError as e:
                print(f"Failed to stop process with PID {self.process.pid}: {e}")
    
    def is_started(self):
        return self.process is not None
    
    def is_alive(self):
        return self.process.poll() is None if self.process else False

