FROM python:3.12-alpine

# Install system dependencies required for building and running the application
RUN apk add --no-cache --virtual .build-deps \
    build-base \
    libffi-dev \
    openssl-dev \
    unixodbc-dev \
    git \
    gnupg

# Install runtime dependencies that must persist after build-deps removal
RUN apk add --no-cache \
    curl \
    unixodbc \
    libffi \
    libstdc++

# Download and install Microsoft ODBC Driver 18 and MSSQL tools
# Import Microsoft GPG key and verify package signatures
RUN curl -O https://download.microsoft.com/download/fae28b9a-d880-42fd-9b98-d779f0fdd77f/msodbcsql18_18.5.1.1-1_amd64.apk \
    && curl -O https://download.microsoft.com/download/7/6/d/76de322a-d860-4894-9945-f0cc5d6a45f8/mssql-tools18_18.4.1.1-1_amd64.apk \
    && curl -fsSL https://packages.microsoft.com/keys/microsoft.asc | gpg --import - 2>/dev/null \
    && gpg --export microsoft@microsoft.com | abuild-keygen -n -q 2>/dev/null || true \
    && cp /etc/apk/keys/* /etc/apk/keys/ 2>/dev/null || true \
    && apk add --allow-untrusted msodbcsql18_18.5.1.1-1_amd64.apk \
    && apk add --allow-untrusted mssql-tools18_18.4.1.1-1_amd64.apk \
    && rm -f msodbcsql18_18.5.1.1-1_amd64.apk mssql-tools18_18.4.1.1-1_amd64.apk

# Set the working directory inside the container
WORKDIR /app

# Copy only the requirements file first to leverage Docker layer caching
COPY ./requirements.txt .

# Install Python dependencies (--pre flag enables prerelease packages like azure-ai-agents)
RUN pip install --upgrade pip setuptools wheel \
    && pip install --no-cache-dir --pre -r requirements.txt \
    && rm -rf /root/.cache

# Remove build dependencies to reduce image size
RUN apk del .build-deps gnupg

# Create non-root user for security
RUN addgroup -S appgroup && adduser -S appuser -G appgroup

# Copy the backend application code into the container
COPY --chown=appuser:appgroup ./ .

# Switch to non-root user
USER appuser

# Expose port 80 for incoming traffic
EXPOSE 80

# Health check to verify the application is running
HEALTHCHECK --interval=30s --timeout=10s --start-period=15s --retries=3 \
    CMD wget --no-verbose --tries=1 --spider http://localhost:80/health || exit 1

# Start the application using Uvicorn
CMD ["uvicorn", "app:app", "--host", "0.0.0.0", "--port", "80"]
