# Dependencies stage - production dependencies only
FROM node:20-alpine AS deps
WORKDIR /app

# Install security updates and ca-certificates
RUN apk update && apk upgrade && apk add --no-cache ca-certificates

# Copy package files
COPY package*.json ./

# Install production dependencies with cache optimization
RUN npm ci --only=production --ignore-scripts && npm cache clean --force

# Build stage - compile and optimize application
FROM node:20-alpine AS builder
WORKDIR /app

# Install security updates and build dependencies
RUN apk update && apk upgrade && apk add --no-cache \
    ca-certificates \
    libc6-compat

# Copy package files and install all dependencies
COPY package*.json ./
RUN npm ci --ignore-scripts && npm cache clean --force

# Copy source code with proper layer caching
COPY . .

# Ensure public directory exists for Next.js
RUN mkdir -p public

# Set build-time environment variables
ENV NEXT_TELEMETRY_DISABLED=1 \
    NODE_ENV=production

# Build the application with optimizations
RUN npm run build && \
    npm prune --production && \
    npm cache clean --force

# Production runtime stage
FROM node:20-alpine AS runtime
WORKDIR /app

# Install security updates, runtime dependencies, and ca-certificates
RUN apk update && apk upgrade && apk add --no-cache \
    ca-certificates \
    curl \
    dumb-init \
    && rm -rf /var/cache/apk/*

# Production environment variables
ENV NODE_ENV=production \
    NEXT_TELEMETRY_DISABLED=1 \
    PORT=3000 \
    HOSTNAME="0.0.0.0" \
    NODE_OPTIONS="--max-old-space-size=1024"

# Create optimized user and group
RUN addgroup -g 1001 -S nodejs && \
    adduser -S nextjs -u 1001 -G nodejs -h /home/nextjs -s /bin/sh

# Create necessary directories with proper permissions
RUN mkdir -p /app/.next /app/public /tmp/nextjs && \
    chown -R nextjs:nodejs /app /tmp/nextjs

# Copy production dependencies
COPY --from=deps --chown=nextjs:nodejs /app/node_modules ./node_modules

# Copy built application files with proper ownership
COPY --from=builder --chown=nextjs:nodejs /app/public ./public
COPY --from=builder --chown=nextjs:nodejs /app/.next ./.next
COPY --from=builder --chown=nextjs:nodejs /app/package.json ./package.json
COPY --from=builder --chown=nextjs:nodejs /app/next.config.js ./next.config.js

# Switch to non-root user
USER nextjs

# Expose application port
EXPOSE 3000

# Enhanced health check for Next.js application
HEALTHCHECK --interval=30s --timeout=15s --start-period=60s --retries=3 \
    CMD curl -f -X GET http://localhost:3000/api/health || curl -f -X GET http://localhost:3000 || exit 1

# Use dumb-init for proper signal handling in containers
ENTRYPOINT ["dumb-init", "--"]
CMD ["npm", "start"]