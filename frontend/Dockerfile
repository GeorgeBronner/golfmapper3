# Build stage for frontend
FROM node:21-alpine AS build

WORKDIR /app

# Copy package files for better layer caching
COPY package*.json ./
RUN npm install
# Install the missing Babel plugin
RUN npm install --save-dev @babel/plugin-transform-react-jsx

# Copy the rest of the app
COPY . .

# Build the static files
ARG VITE_SERVER_IP
ENV VITE_SERVER_IP=$VITE_SERVER_IP
RUN npm run build

# The static files will be in /frontend/dist