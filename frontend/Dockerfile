# Build stage
FROM node:18-alpine as build-stage

# Set proxy environment variables
ENV HTTP_PROXY=http://Zf5ACR:hW71hL@138.219.72.55:8000
ENV HTTPS_PROXY=http://Zf5ACR:hW71hL@138.219.72.55:8000
ENV NO_PROXY=localhost,127.0.0.1,db,backend,frontend,nginx

# Set API URL for production
ENV VUE_APP_API_URL=/api

# Update package index and install system dependencies for node-gyp
RUN apk update && apk add --no-cache python3 make g++

# Set working directory
WORKDIR /app

# Copy package files first for better layer caching
COPY package*.json ./

# Use BuildKit cache for npm and deterministic installs with lockfile
RUN --mount=type=cache,target=/root/.npm \
	npm ci --no-audit --no-fund

# Copy source code
COPY . .

# Build the application
RUN npm run build

# Production stage
FROM nginx:stable-alpine as production-stage

# Copy built files to nginx
COPY --from=build-stage /app/dist /usr/share/nginx/html

# Copy nginx configuration
COPY nginx.conf /etc/nginx/conf.d/default.conf

# Expose port
EXPOSE 80

# Start nginx
CMD ["nginx", "-g", "daemon off;"]
