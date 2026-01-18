# Base image: Ubuntu 22.04
FROM ubuntu:22.04

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    build-essential \
    cmake \
    curl \
    wget \
    gpg \
    git \
    pkg-config \
    libssl-dev \
    libcurl4-openssl-dev \
    libgl1-mesa-dev \
    mesa-common-dev \
    libegl1-mesa-dev \
    libgles2-mesa-dev \
    libv4l-dev \
    libunwind-dev \
    && rm -rf /var/lib/apt/lists/*

# Install CMake 3.27.0+ from Kitware (Ubuntu 22.04 comes with 3.22.1)
RUN apt-get update && apt-get install -y lsb-release && \
    wget -O - https://apt.kitware.com/keys/kitware-archive-latest.asc | \
    gpg --dearmor - | tee /etc/apt/trusted.gpg.d/kitware.gpg >/dev/null && \
    echo "deb https://apt.kitware.com/ubuntu/ jammy main" | \
    tee /etc/apt/sources.list.d/kitware.list >/dev/null && \
    apt-get update && apt-get install -y cmake && \
    rm -rf /var/lib/apt/lists/*

# Install Presage SDK from official PPA
RUN curl -s "https://presage-security.github.io/PPA/KEY.gpg" | gpg --dearmor | \
    tee /etc/apt/trusted.gpg.d/presage-technologies.gpg >/dev/null && \
    curl -s --compressed -o /etc/apt/sources.list.d/presage-technologies.list \
    "https://presage-security.github.io/PPA/presage-technologies.list" && \
    apt-get update && \
    apt-get install -y libphysiologyedge-dev && \
    apt-get install -y libsmartspectra-dev=2.0.4 && \
    rm -rf /var/lib/apt/lists/*

# Copy source code
COPY hello_vitals.cpp CMakeLists.txt ./
COPY PATCH.md ./

# Build
RUN mkdir -p build && cd build && \
    cmake .. && \
    make -j$(nproc) && \
    cd ..

# Copy startup script
COPY start-server.sh ./
RUN chmod +x ./start-server.sh

# Expose port (if running as HTTP server)
EXPOSE 8080

# Default: run hello_vitals as interactive
CMD ["./build/hello_vitals"]
