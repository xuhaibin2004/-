FROM node:20-alpine AS build

WORKDIR /app

ENV HTTP_PROXY= \
    HTTPS_PROXY= \
    http_proxy= \
    https_proxy=

COPY frontend/package.json .
RUN npm config set proxy null && \
    npm config set https-proxy null && \
    npm install --registry https://registry.npmmirror.com

COPY frontend/ .
RUN npm run build

FROM nginx:alpine

COPY --from=build /app/dist /usr/share/nginx/html
COPY nginx.conf /etc/nginx/conf.d/default.conf

EXPOSE 80

CMD ["nginx", "-g", "daemon off;"]
