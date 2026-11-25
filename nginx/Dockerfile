FROM node:24.22.3-slim AS vendor
WORKDIR /v
RUN npm pack monaco-editor@0.52.2 marked@12.0.2 @fontsource/inter-tight@5.2.5 @fontsource/geist-mono@5.2.5 >/dev/null \
 && mkdir monaco marked it gm fonts \
 && tar xzf monaco-editor-0.52.2.tgz -C monaco \
 && tar xzf marked-12.0.2.tgz -C marked \
 && tar xzf fontsource-inter-tight-5.2.5.tgz -C it \
 && tar xzf fontsource-geist-mono-5.2.5.tgz -C gm \
 && cp it/package/files/inter-tight-latin-400-normal.woff2 it/package/files/inter-tight-latin-500-normal.woff2 \
       it/package/files/inter-tight-latin-600-normal.woff2 gm/package/files/geist-mono-latin-400-normal.woff2 \
       gm/package/files/geist-mono-latin-500-normal.woff2 fonts/ \
 && cp it/package/LICENSE fonts/LICENSE-inter-tight.txt && cp gm/package/LICENSE fonts/LICENSE-geist-mono.txt

FROM node:24.22.3-slim AS ui
WORKDIR /ui
COPY ui/package.json ui/package-lock.json ./
RUN npm ci --no-audit --no-fund
COPY ui/ ./
RUN npm run build

FROM nginx:1.31.10-alpine
COPY nginx/nginx.conf /etc/nginx/conf.d/default.conf
COPY --from=ui /ui/dist/ /usr/share/nginx/html/
COPY --from=vendor /v/monaco/package/min/vs /usr/share/nginx/html/vendor/monaco/vs
COPY --from=vendor /v/marked/package/marked.min.js /usr/share/nginx/html/vendor/marked.min.js
COPY --from=vendor /v/fonts /usr/share/nginx/html/vendor/fonts
