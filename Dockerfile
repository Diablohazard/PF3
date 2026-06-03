# Use an official Python runtime as a parent image
FROM python:3.9-slim

# Set the working directory in the container
WORKDIR /app

# Install build dependencies needed by source Python packages on slim images
RUN apt-get update \
    && apt-get install -y --no-install-recommends \
        build-essential \
        gcc \
        libffi-dev \
        libssl-dev \
        libxml2-dev \
        libxslt1-dev \
    && rm -rf /var/lib/apt/lists/*

# Install Python dependencies first to improve Docker layer caching
COPY requirements.txt /app/requirements.txt
RUN python -m pip install --upgrade pip setuptools wheel
RUN python -m pip install --prefer-binary --no-cache-dir flask==3.0.3
RUN python -m pip install --prefer-binary --no-cache-dir mysql-connector-python==8.4.0
RUN python -m pip install --prefer-binary --no-cache-dir opcua==0.98.13
RUN python -m pip install --prefer-binary --no-cache-dir asyncua==1.0.6
RUN python -m pip install --prefer-binary --no-cache-dir pymysql==1.1.1
RUN python -m pip install --prefer-binary --no-cache-dir python-dotenv==1.0.1
RUN python -m pip install --prefer-binary --no-cache-dir sqlalchemy==2.0.30

# Copy the current directory contents into the container at /app
COPY . /app

# Make container app port available
EXPOSE 8180

# Define environment variable
ENV NAME=World

# Run app.py when the container launches
CMD ["python", "app/app.py"]
