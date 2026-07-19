# Static-site image for the AtlasPrimeX marketing website.
# Serves the plain HTML/CSS/JS in this folder with Caddy. No build step, no Node.
FROM caddy:2-alpine

# Site files
COPY index.html styles.css main.js /srv/
COPY assets /srv/assets
COPY favicon.ico favicon.png /srv/
COPY Caddyfile /etc/caddy/Caddyfile

# Railway sets $PORT at runtime; Caddyfile reads it.
CMD ["caddy", "run", "--config", "/etc/caddy/Caddyfile", "--adapter", "caddyfile"]
