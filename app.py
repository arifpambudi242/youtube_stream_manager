from datetime import datetime, timedelta
from apscheduler.schedulers.background import BackgroundScheduler
from app import *
from app.models import Streams, User, seed, Subscription


# cron job check scheduled stream needs to action
def check_scheduled_stream():
    '''
    Check scheduled stream every 10 seconds
    whether stream is start or stop
    '''
    with app.app_context():  # Menambahkan konteks aplikasi
        streams = Streams.query.all()
        subscription = Subscription.query.all()
        for sub in subscription:
            if sub.end_at and datetime.now() - sub.end_at <= timedelta(seconds=10):
                subcr = Subscription.query.filter_by(id=sub.id).first()
                subcr.is_active = False
                subcr.end_at = datetime.now()
                db.session.commit()
        for stream in streams:
            # start_at == current_time start stream
            if stream.is_active and stream.start_at and stream.start_at - datetime.now() == timedelta(seconds=1):
                # check if stream is already started
                if not stream.is_started():
                    stream_ = Streams.query.filter_by(id=stream.id).first()
                    # start stream
                    stream_.pid = start_stream_youtube(stream_.video.path, stream_.kode_stream, repeat=stream_.is_repeat)
                    stream_.is_active = True
                    db.session.commit()

            # end_at == current_time stop stream
            if stream.is_active and stream.end_at and stream.end_at - datetime.now() == timedelta(seconds=1):
                # check if stream is already started
                print(f'selisih end at - current time {stream.end_at - datetime.now()}')
                stream_ = Streams.query.filter_by(id=stream.id).first()
                if stream.is_started():
                    # stop stream
                    is_stream_alive = is_stream_started(stream_.pid)
                    if is_stream_alive and stream_.pid:
                        stopped = stop_stream_by_pid(stream_.pid)
                        if stopped:
                            print(f'stream stopped end at pid  {stream_.pid} ')
                    stream_.pid = None
                    stream_.is_active = False
                    db.session.commit()

            sub = Subscription.query.filter_by(user_id=stream.user_id, is_active=True).first()
            if stream.is_active and not sub:
                stream_ = Streams.query.filter_by(id=stream.id).first()
                # check if stream is already started
                if stream_.is_started():
                    # stop stream
                    is_stream_alive = is_stream_started(stream_.pid)
                    if is_stream_alive and stream_.pid:
                        stopped = stop_stream_by_pid(stream_.pid)
                        if stopped:
                            print(f'stream stopped pid  {stream_.pid} ')
                    stream_.pid = None
                    stream_.is_active = False
                    db.session.commit()
            
            

if __name__ == "__main__":
    # check scheduled stream every 1 seconds
    import os
    from dotenv import load_dotenv
    load_dotenv()
    DEBUG = os.getenv("DEBUG")
    # print .env location
    print(os.getenv("DOTENV_LOCATION"))
    print(DEBUG)
    scheduler = BackgroundScheduler()
    scheduler.add_job(func=check_scheduled_stream, trigger="interval", seconds=1)
    scheduler.start()
    with app.app_context():
        seed()
    app.run(debug=DEBUG, port=5000, host='0.0.0.0')