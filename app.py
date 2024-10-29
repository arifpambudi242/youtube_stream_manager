from datetime import datetime, timedelta
from apscheduler.schedulers.background import BackgroundScheduler
from app import *
from app.models import Streams, seed
def check_youtube_stream(stream_url):
    """
    Memeriksa apakah ada stream aktif di server RTMP YouTube menggunakan `ffmpeg`.
    
    Parameters:
    stream_url (str): URL lengkap RTMP YouTube (termasuk stream key).

    Returns:
    bool: True jika stream aktif, False jika tidak.
    """
    try:
        # Jalankan perintah ffmpeg untuk memeriksa aliran streaming
        result = subprocess.run(
            ["ffmpeg", "-i", stream_url, "-t", "3", "-f", "null", "-"],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            timeout=10
        )
        # Cek apakah hasil stderr mengandung pesan "Input/output error" atau serupa, 
        # yang menandakan bahwa stream tidak aktif
        if b"Input/output error" in result.stderr or b"Could not" in result.stderr:
            return False
        return True
    except subprocess.TimeoutExpired:
        # Jika ffmpeg timeout, kemungkinan besar stream tidak aktif
        return False

# cron job check scheduled stream needs to action
def check_scheduled_stream():
    '''
    Check scheduled stream every 10 seconds
    whether stream is start or stop
    '''
    with app.app_context():  # Menambahkan konteks aplikasi
        streams = Streams.query.all()
        for stream in streams:
            # start_at >= current_time start stream
            if stream.start_at and stream.start_at - datetime.now() <= timedelta(seconds=10):
                # check if stream is already started
                if not stream.is_started():
                    # start stream
                    stream.pid = start_stream_youtube(stream.video.path, stream.kode_stream, repeat=stream.is_repeat)
                    stream.is_active = True
                    db.session.commit()
                    
            # end_at >= current_time stop stream
            if stream.is_active and stream.end_at and stream.end_at - datetime.now() <= timedelta(seconds=10):
                # check if stream is already started
                if stream.is_started():
                    # stop stream
                    is_stream_alive = check_youtube_stream(f'rtmp://a.rtmp.youtube.com/live2/{stream.kode_stream}')
                    if is_stream_alive and stream.pid:
                        stop_stream_by_pid(stream.pid)
                    stream.pid = None
                    stream.is_active = False
                    db.session.commit()
            
            if stream.is_active and stream.is_repeat and stream.end_at and stream.end_at - datetime.now() <= timedelta(seconds=10):
                # check if stream is already started
                if stream.is_started():
                    # stop stream
                    is_stream_alive = check_youtube_stream(f'rtmp://a.rtmp.youtube.com/live2/{stream.kode_stream}')
                    if is_stream_alive and stream.pid:
                        stop_stream_by_pid(stream.pid)
                    stream.pid = None
                    stream.is_active = False
                    db.session.commit()
            
            

if __name__ == "__main__":
    # check scheduled stream every 10 seconds
    import os
    from dotenv import load_dotenv
    load_dotenv()
    DEBUG = os.getenv("DEBUG")
    # print .env location
    print(os.getenv("DOTENV_LOCATION"))
    print(DEBUG)
    scheduler = BackgroundScheduler()
    scheduler.add_job(func=check_scheduled_stream, trigger="interval", seconds=9)
    scheduler.start()
    with app.app_context():
        seed()
    app.run(debug=DEBUG, port=5000, host='0.0.0.0')