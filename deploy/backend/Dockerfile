FROM python:3.15.2-slim
WORKDIR /app
COPY backend/requirements.txt /app/backend/
RUN pip install --no-cache-dir -r /app/backend/requirements.txt
# /app is laid out like the repo, so the code finds tools/ and catalog/ next to backend/ the same way in a checkout
COPY backend/server.py /app/backend/
COPY backend/lab/ /app/backend/lab/
COPY backend/sandbox/ /app/backend/sandbox/
COPY tools/pack.py /app/tools/
COPY catalog/ /app/catalog/
ENV PYTHONUNBUFFERED=1 PYTHONDONTWRITEBYTECODE=1
# gate.py and grade.py run from here, so `docker compose run backend python3 gate.py /set` keeps working
WORKDIR /app/backend/sandbox
EXPOSE 8000
CMD ["python3", "/app/backend/server.py"]
