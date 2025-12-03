# Use Python 3.11 (stable and compatible with audioop)
FROM python:3.11-slim

# Install system dependencies (needed for audio processing if we expand later)
RUN apt-get update && apt-get install -y \
    gcc \
    portaudio19-dev \
    ca-certificates \
    && rm -rf /var/lib/apt/lists/*

# Set working directory
WORKDIR /app
ENV PYTHONUNBUFFERED=1


# Copy requirements first to leverage Docker cache
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy the rest of the application
COPY . .

# Expose SIP and RTP ports
EXPOSE 5060/udp
EXPOSE 10000/udp

# Run the application
CMD ["python", "-m", "src.main"]
