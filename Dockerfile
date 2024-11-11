# Gunakan image dasar dengan Python 3.11.2
FROM python:3.11.2-slim

# Install dependencies
RUN apt-get update && \
    apt-get install -y ffmpeg && \
    apt-get clean && \
    rm -rf /var/lib/apt/lists/*

# Set working directory di dalam container
WORKDIR /app

# Salin requirements.txt terlebih dahulu untuk memanfaatkan caching Docker
COPY requirements.txt /app/

# Install dependencies dari requirements.txt
RUN pip install --no-cache-dir -r requirements.txt && \
    pip install --no-cache-dir --upgrade pip

# Salin seluruh aplikasi (termasuk folder app) ke dalam container
COPY app /app/app

# Expose port Flask
EXPOSE 5000

# Menjalankan aplikasi Flask
CMD ["python", "app/app.py"]