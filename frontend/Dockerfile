# Stage 1: Build React App
FROM node:22-alpine as builder

WORKDIR /app

# Install dependencies
COPY package*.json ./
RUN npm install

# Build the app
# VITE_API_URL is intentionally left empty so the frontend uses relative paths (/api/...)
COPY . .
RUN npm run build

# Stage 2: Serve with Nginx
FROM nginx:alpine

# Remove default nginx static assets and config
RUN rm -rf /usr/share/nginx/html/*

# Copy custom nginx config (reverse proxy to backend)
COPY nginx.conf /etc/nginx/conf.d/default.conf

# Copy static assets from builder stage
COPY --from=builder /app/dist /usr/share/nginx/html

# Expose port (Nginx default)
EXPOSE 80

# Start Nginx
CMD ["nginx", "-g", "daemon off;"]
