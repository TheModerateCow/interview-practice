# pytest 9.2.0 (the runner's version) for pyright to resolve in candidates' tests; pyright finds it through extraPaths. Offline at run time.
FROM python:3.15.2-slim AS py
RUN pip install --no-cache-dir --target /site pytest==9.2.0
FROM node:24.22.3-slim
RUN npm install -g pyright@1.1.414 && npm cache clean --force
COPY --from=py /site /opt/site
