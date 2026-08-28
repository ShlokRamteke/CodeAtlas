FROM oven/bun:1-alpine

WORKDIR /app

# Copy contracts first and build
COPY packages/contracts ./packages/contracts
WORKDIR /app/packages/contracts
RUN bun install && bun run build

# Copy frontend and install dependencies
WORKDIR /app/frontend
COPY frontend/package.json ./
RUN bun install

# Copy frontend application code
COPY frontend ./

EXPOSE 3000

ENV PORT=3000
ENV HOSTNAME="0.0.0.0"
ENV NEXT_PUBLIC_API_URL="http://localhost:8000"

CMD ["bun", "run", "dev"]
