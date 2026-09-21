FROM node:22-slim AS build
WORKDIR /app
COPY frontend/package.json frontend/package-lock.json ./
RUN npm ci --no-audit --no-fund
COPY frontend/ ./
ENV VITE_API_BASE_URL=""
RUN npm run build

FROM nginx:alpine
COPY --from=build /app/dist /usr/share/nginx/html
COPY docker/producer-preview/nginx.conf /etc/nginx/conf.d/default.conf
