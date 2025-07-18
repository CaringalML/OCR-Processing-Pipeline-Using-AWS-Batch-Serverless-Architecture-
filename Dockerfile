# Use the most recent secure Node.js LTS Alpine image
FROM node:20.18.0-alpine3.20

# Set working directory
WORKDIR /app

# Copy package files first
COPY package*.json ./

# Install dependencies as root user
RUN npm install --omit=dev && npm cache clean --force

# Copy the rest of the application code
COPY . .

# Create a non-root user and change ownership
RUN addgroup -g 1001 -S nodejs && \
    adduser -S nodejs -u 1001 -G nodejs && \
    chown -R nodejs:nodejs /app

# Switch to non-root user
USER nodejs

# Expose port (not necessary for AWS Batch but good practice)
EXPOSE 3000

# Add health check
HEALTHCHECK --interval=30s --timeout=3s --start-period=5s --retries=3 \
  CMD node -e "require('http').get('http://localhost:3000/health', (res) => { process.exit(res.statusCode === 200 ? 0 : 1) })"

# Command to run the application
CMD ["node", "index.js"]