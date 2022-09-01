FROM python:slim

RUN apt update && apt install -y g++ gcc libevent-dev libxslt-dev ffmpeg

WORKDIR /app
COPY . .

RUN pip3 install --no-cache-dir -r requirements.txt

ENTRYPOINT [ "python3", "aniGamerPlus.py" ]
