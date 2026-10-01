FROM python:3.12-slim

WORKDIR /app
COPY requirements.txt /app/requirements.txt
RUN python -m pip install --no-cache-dir --disable-pip-version-check -r /app/requirements.txt
COPY ipod_backup.py /app/ipod_backup.py
COPY LICENSE /app/LICENSE

ENTRYPOINT ["python", "/app/ipod_backup.py"]
