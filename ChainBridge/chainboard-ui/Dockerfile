FROM node:18-alpine

WORKDIR /app

# Install dependencies
COPY package*.json ./
RUN npm ci --legacy-peer-deps

# Copy source
COPY . .

# Build (optional, for production)
# RUN npm run build

# Expose port
EXPOSE 3000

# Start dev server
CMD ["npm", "start"]
