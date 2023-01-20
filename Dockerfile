FROM python:3.10
RUN apt-get update
RUN apt-get install ffmpeg libsm6 libxext6 -y
COPY requirements.txt .
RUN pip install -r requirements.txt
COPY . /app
WORKDIR /app
RUN rm -rf .env
RUN mkdir -p /data
CMD ["python", "main.py"]