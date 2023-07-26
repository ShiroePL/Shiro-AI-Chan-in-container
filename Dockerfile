# Use Ubuntu as base image
FROM ubuntu:latest

# Install Python3.9 and pip
RUN apt-get update && apt-get install -y software-properties-common
RUN add-apt-repository ppa:deadsnakes/ppa
RUN apt-get update && apt-get install -y python3.9 python3-pip

# Set Python 3.9 as the default Python version
RUN update-alternatives --install /usr/bin/python3 python3 /usr/bin/python3.9 1

# Install ZeroTier
RUN curl -s https://install.zerotier.com | bash

# Create a directory for the app
WORKDIR /app

# Install Python dependencies
COPY requirements.txt ./
RUN pip3 install -r requirements.txt

# Copy the rest of the application
COPY . .

# Copy the startup script
COPY startup.sh .
RUN chmod +x startup.sh

# Expose the application's port
EXPOSE 8057

# Run the application
CMD ["./startup.sh"]
