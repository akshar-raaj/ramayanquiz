# Use an official Python image as a base
FROM python:3.10-slim

# Set the working directory to /app
WORKDIR /app

# Copy the requirements file
COPY requirements.txt .

# Install the dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy the application code
# TODO: Remove copying it, instead mount it as a volume.
# This will allow modifying code without rebuilding the image
COPY . .

# Expose the port that the application will run on
# It doesn't actually publish the port, but instead works as a documentation
EXPOSE 8000

# Run the command to start the development server
# CMD format instead of EXEC format
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
