FROM node:21-alpine

# Add necessary build tools for potential native dependencies
RUN apk add --no-cache python3 make g++

WORKDIR /usr/src/app

# Copy package files first for better layer caching
COPY package*.json ./
RUN npm install

# Install babel dependencies explicitly
RUN npm install --save-dev @babel/core @babel/preset-env @babel/preset-react @babel/plugin-transform-runtime

# Copy the rest of the app
COPY . .

# Build the app with environment variables
ARG VITE_SERVER_IP
ENV VITE_SERVER_IP=$VITE_SERVER_IP

# Expose port
EXPOSE 3000

# Start the app with development server
CMD ["npm", "run", "dev", "--", "--host", "0.0.0.0"]