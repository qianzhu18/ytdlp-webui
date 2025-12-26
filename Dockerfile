FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

ARG APT_MIRROR=mirrors.tuna.tsinghua.edu.cn

RUN sed -i.bak -E "s#http://deb.debian.org/debian#https://${APT_MIRROR}/debian#g; s#http://deb.debian.org/debian-security#https://${APT_MIRROR}/debian-security#g" /etc/apt/sources.list.d/debian.sources \
    && apt-get update \
    && apt-get install -y --no-install-recommends ffmpeg ca-certificates \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY webui/ /app/

ENV DOWNLOAD_DIR=/downloads
EXPOSE 8080

CMD ["python", "app.py"]
