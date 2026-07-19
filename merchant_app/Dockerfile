# Stage 1 — build the Flutter web app
# Pinned to 3.44.6 (Dart 3.12.2) to satisfy the pubspec SDK constraint (^3.12.2).
# The floating :stable tag currently ships Dart 3.12.0, which fails `flutter pub get`.
FROM ghcr.io/cirruslabs/flutter:3.44.6 AS build
WORKDIR /app
COPY . .
RUN flutter pub get
RUN flutter build web --release

# Stage 2 — serve the static build with Caddy
FROM caddy:alpine
COPY --from=build /app/build/web /usr/share/caddy
COPY Caddyfile /etc/caddy/Caddyfile
