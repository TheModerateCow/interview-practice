FROM python:3.15.2-slim
WORKDIR /app
COPY backend/requirements.txt /app/
RUN pip install --no-cache-dir -r /app/requirements.txt
COPY backend/runner.py backend/grade.py backend/gate.py backend/server.py tools/pack.py /app/
ENV PYTHONUNBUFFERED=1 PYTHONDONTWRITEBYTECODE=1
EXPOSE 8000
CMD ["python3", "/app/server.py"]
