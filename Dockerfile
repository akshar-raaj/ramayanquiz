# Use an official Python image as a base
# A slim image is smaller and stripped down, thus leading to smaller image builds
# Thus leading to faster downloads and faster deployments
FROM python:3.10-slim

# Install dependencies
# Combine multiple commands into a single RUN to ensure
# efficient layer and caching
# We need curl for HEALTHCHECK later down the line
RUN apt-get update && apt-get install -y --no-install-recommends curl \
    && apt-get clean && rm -rf /var/lib/apt/lists/*

# Set the working directory to /app
WORKDIR /app

# Copy the requirements file
COPY requirements.txt .
# Don't copy the entire source code, we will utilize bind mounts
# This allows us to modify code during container run without needing an image build.

# Install the dependencies
RUN pip install -r requirements.txt

# Expose the port that the application will run on
# It doesn't actually publish the port, but instead works as a documentation
# A best practice
EXPOSE 8000

# Add Healthcheck
HEALTHCHECK --timeout=5s CMD curl -f http://localhost:8000/_health || exit 1

# Run the command to start the development server
# CMD EXEC format instead of SHELL format
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
