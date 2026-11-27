FROM node:22-alpine AS build

WORKDIR /app

COPY frontend/package.json frontend/package-lock.json ./
RUN npm ci

COPY frontend/ ./
ARG VITE_CSRF_COOKIE=parkify_csrf
ENV VITE_CSRF_COOKIE=$VITE_CSRF_COOKIE
RUN npm run build

FROM nginx:1.27-alpine

COPY docker/frontend/nginx.conf /etc/nginx/conf.d/default.conf
COPY --from=build /app/dist /usr/share/nginx/html

EXPOSE 80
