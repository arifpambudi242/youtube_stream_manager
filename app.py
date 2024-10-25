from datetime import datetime
from apscheduler.schedulers.background import BackgroundScheduler
from app import *
from app.models import Streams, seed
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
            if stream.start_at and stream.start_at <= datetime.utcnow():
                # check if stream is already started
                if not stream.is_started():
                    # start stream
                    stream.pid = start_stream_youtube(stream.video.path, stream.kode_stream, repeat=stream.is_repeat)
                    stream.is_active = True
                    db.session.commit()
            # end_at >= current_time stop stream
            if stream.end_at and stream.end_at <= datetime.utcnow():
                # check if stream is already started
                if stream.is_started():
                    # stop stream
                    stop_stream(stream.pid)
                    stream.pid = None
                    stream.is_active = False
                    db.session.commit()

if __name__ == "__main__":
    # check scheduled stream every 10 seconds
    scheduler = BackgroundScheduler()
    scheduler.add_job(func=check_scheduled_stream, trigger="interval", seconds=1)
    scheduler.start()
    with app.app_context():
        seed()
    app.run(debug=True, port=5000, host='0.0.0.0')