FROM python:3.15.2-slim
WORKDIR /app
COPY backend/requirements.txt /app/
RUN pip install --no-cache-dir -r /app/requirements.txt
COPY backend/server.py /app/
COPY backend/lab/ /app/lab/
COPY backend/sandbox/ /app/sandbox/
COPY tools/pack.py /app/lab/
COPY presets/ /app/presets/
ENV PYTHONUNBUFFERED=1 PYTHONDONTWRITEBYTECODE=1
# gate.py and grade.py run from here, so `docker compose run backend python3 gate.py /set` keeps working
WORKDIR /app/sandbox
EXPOSE 8000
CMD ["python3", "/app/server.py"]
