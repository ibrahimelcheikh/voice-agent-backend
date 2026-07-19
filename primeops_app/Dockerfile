# Multi-stage: build the Flutter web app, then serve it with Caddy.
# Build args select mock vs live backend (Flutter bakes dart-defines at build time):
#   docker build --build-arg USE_MOCK=false --build-arg API_BASE=https://your-backend .
# On Railway, set USE_MOCK and API_BASE as service (build) variables.
FROM ghcr.io/cirruslabs/flutter:3.44.6 AS build
ARG USE_MOCK=true
ARG API_BASE=
WORKDIR /app
COPY pubspec.yaml pubspec.lock ./
RUN flutter pub get
COPY . .
RUN flutter build web --release --no-web-resources-cdn --no-tree-shake-icons \
    --dart-define=USE_MOCK=${USE_MOCK} --dart-define=API_BASE=${API_BASE}

FROM caddy:2-alpine
COPY --from=build /app/build/web /srv
COPY Caddyfile /etc/caddy/Caddyfile
CMD ["caddy", "run", "--config", "/etc/caddy/Caddyfile", "--adapter", "caddyfile"]
