# Gunakan image dasar dengan Python 3.11.2
FROM python:3.11.2-slim

# Install dependencies
RUN apt-get update && apt-get install -y ffmpeg

# Set working directory di dalam container
WORKDIR /

# Salin aplikasi dan requirements.txt ke dalam container
COPY . /

# Install dependencies dari requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

# Jalankan aplikasi menggunakan gunicorn (lebih efisien daripada flask server)
CMD ["python", "app.py"]
