FROM python:3

COPY . /app
WORKDIR /app
RUN set -x \
    && apt update \
    && apt install g++ gcc libevent-dev libxslt-dev ffmpeg -y \
    && pip3 install greenlet lxml \
    && pip install --no-cache-dir -r requirements.txt
EXPOSE 5000
CMD python3 aniGamerPlus.py
