# Stage 1: Build
FROM node:18-alpine as builder

WORKDIR /app

# 复制依赖文件 (注意路径，因为构建上下文是项目根目录)
COPY frontend/package*.json ./
RUN npm install

# 复制源码并构建
COPY frontend/ .
RUN npm run build

# Stage 2: Run
FROM nginx:alpine

# 复制构建产物
COPY --from=builder /app/dist /usr/share/nginx/html

# 复制 Nginx 配置 (从根目录的 nginx/default.conf)
COPY nginx/default.conf /etc/nginx/conf.d/default.conf

EXPOSE 80

CMD ["nginx", "-g", "daemon off;"]
