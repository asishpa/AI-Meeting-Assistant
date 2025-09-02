FROM python:3.11-slim

# Install deps
RUN apt-get update && apt-get install -y \
    chromium \
    chromium-driver \
    pulseaudio \
    ffmpeg \
    && rm -rf /var/lib/apt/lists/*

# Install Python deps
WORKDIR /app
COPY requirements.txt .
RUN pip install -r requirements.txt

COPY . .

# Run meeting recorder entrypoint
ENTRYPOINT ["python", "-m", "app.services.meetings.run_meeting"]
