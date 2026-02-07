###############################################################################
# Stage 1: Build — install Python dependencies with build tools
###############################################################################
FROM python:3.12-alpine AS builder

# Install build-only system dependencies
RUN apk add --no-cache --virtual .build-deps \
    build-base \
    libffi-dev \
    openssl-dev \
    unixodbc-dev \
    git

WORKDIR /build

# Copy only the requirements file first to leverage Docker layer caching
COPY ./requirements.txt .

# Install Python dependencies into a target directory for clean copy
RUN pip install --upgrade pip setuptools wheel \
    && pip install --no-cache-dir --pre --target /build/deps -r requirements.txt

###############################################################################
# Stage 2: Runtime — minimal image with only runtime dependencies
###############################################################################
FROM python:3.12-alpine

# Install runtime-only system dependencies
RUN apk add --no-cache \
    curl \
    unixodbc \
    libffi \
    libstdc++ \
    gnupg

# Download and install Microsoft ODBC Driver 18 and MSSQL tools
RUN curl -O https://download.microsoft.com/download/fae28b9a-d880-42fd-9b98-d779f0fdd77f/msodbcsql18_18.5.1.1-1_amd64.apk \
    && curl -O https://download.microsoft.com/download/7/6/d/76de322a-d860-4894-9945-f0cc5d6a45f8/mssql-tools18_18.4.1.1-1_amd64.apk \
    && curl https://packages.microsoft.com/keys/microsoft.asc | gpg --import - 2>/dev/null \
    && apk add --allow-untrusted msodbcsql18_18.5.1.1-1_amd64.apk \
    && apk add --allow-untrusted mssql-tools18_18.4.1.1-1_amd64.apk \
    && rm msodbcsql18_18.5.1.1-1_amd64.apk mssql-tools18_18.4.1.1-1_amd64.apk \
    && apk del gnupg

# Set the working directory inside the container
WORKDIR /app

# Copy Python dependencies from builder stage
COPY --from=builder /build/deps /usr/local/lib/python3.12/site-packages/

# Create non-root user for security
RUN addgroup -S appgroup && adduser -S appuser -G appgroup

# Copy the backend application code into the container
COPY ./ .

# Switch to non-root user
USER appuser

# Expose port 80 for incoming traffic
EXPOSE 80

# Health check to verify the application is running
HEALTHCHECK --interval=30s --timeout=10s --start-period=15s --retries=3 \
    CMD wget --no-verbose --tries=1 --spider http://localhost:80/health || exit 1

# Start the application using Uvicorn
CMD ["uvicorn", "app:app", "--host", "0.0.0.0", "--port", "80"]
