# Stage 1: Build
FROM node:18-alpine as builder

WORKDIR /app

# 设置 npm 镜像加速
RUN npm config set registry https://registry.npmmirror.com

# 复制所有源码 (包括可能存在的 node_modules)
COPY frontend/ .

# 强制清理并重新安装依赖 (确保是 Linux 版本的二进制文件)
RUN rm -rf node_modules package-lock.json
RUN npm install

# 构建
RUN npm run build

# Stage 2: Run
FROM nginx:alpine

# 复制构建产物
COPY --from=builder /app/dist /usr/share/nginx/html

# 复制 Nginx 配置 (从根目录的 nginx/default.conf)
COPY nginx/default.conf /etc/nginx/conf.d/default.conf

EXPOSE 80

CMD ["nginx", "-g", "daemon off;"]
