# ---- Stage 1: Build ----
FROM node:20-alpine AS build
WORKDIR /app

COPY package*.json ./
RUN npm ci --prefer-offline

COPY . .
# VITE_API_URL is baked in at build time; override via build-arg in docker-compose
ARG VITE_API_URL=/api
ENV VITE_API_URL=$VITE_API_URL
RUN npm run build

# ---- Stage 2: Serve with nginx + HTTPS ----
FROM nginx:1.27-alpine
COPY --from=build /app/dist /usr/share/nginx/html

RUN printf 'server {\n\
  listen 80;\n\
  return 301 https://$host$request_uri;\n\
}\n\
server {\n\
  listen 443 ssl;\n\
  ssl_certificate /etc/letsencrypt/live/cloudreconai.mooo.com/fullchain.pem;\n\
  ssl_certificate_key /etc/letsencrypt/live/cloudreconai.mooo.com/privkey.pem;\n\
  ssl_protocols TLSv1.2 TLSv1.3;\n\
  ssl_ciphers HIGH:!aNULL:!MD5;\n\
  root /usr/share/nginx/html;\n\
  index index.html;\n\
  location /api/ {\n\
    proxy_pass http://backend:8080/api/;\n\
    proxy_set_header Host $host;\n\
    proxy_set_header X-Real-IP $remote_addr;\n\
    proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;\n\
    proxy_set_header X-Forwarded-Proto $scheme;\n\
    proxy_read_timeout 300;\n\
    client_max_body_size 512m;\n\
  }\n\
  location / {\n\
    try_files $uri $uri/ /index.html;\n\
  }\n\
}\n' > /etc/nginx/conf.d/default.conf

EXPOSE 80 443
