# Сборка: Vite собирает сайт в dist/
FROM node:22-alpine AS build
WORKDIR /app
COPY package.json package-lock.json ./
RUN npm ci --no-fund --no-audit
COPY . .
RUN npm run build

# Раздача готовых файлов
FROM nginx:1.27-alpine
# openssl — зашифровать общий пароль на сайт, если он задан (SITE_PASSWORD)
RUN apk add --no-cache openssl && touch /etc/nginx/site-auth.conf
COPY --from=build /app/dist /usr/share/nginx/html
COPY nginx.conf /etc/nginx/conf.d/default.conf
COPY --chmod=755 site-password.sh /docker-entrypoint.d/40-site-password.sh
EXPOSE 80
