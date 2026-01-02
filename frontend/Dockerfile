FROM node:18-alpine

WORKDIR /app

# Copy package files
COPY package*.json ./

# Install deps
RUN npm install

# Copy app
COPY . .

# ✅ Add curl for HEALTHCHECK (alpine doesn't have it by default)
RUN apk add --no-cache curl

# ✅ Ensure the dev server binds to all interfaces in the container
ENV HOST=0.0.0.0
ENV PORT=3000

# Non-root
RUN addgroup -g 1001 -S nodejs
RUN adduser -S nextjs -u 1001
RUN chown -R nextjs:nodejs /app
USER nextjs

EXPOSE 3000

# Health check hits the dev server directly
HEALTHCHECK --interval=30s --timeout=30s --start-period=5s --retries=3 \
  CMD curl -f http://localhost:3000 || exit 1

CMD ["npm", "start"]
