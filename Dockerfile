# Use the official Python image as a parent image
FROM python:3.11.6-slim

# Set the working directory in the container
WORKDIR /app

# Install ffmpeg and git
RUN apt-get update && \
    apt-get install -y ffmpeg git && \
    apt-get clean && \
    rm -rf /var/lib/apt/lists/*

# Clone Repository
RUN git clone https://github.com/ashutoshdhanda/meeting_summary.git

# Set the working directory for installing python dependencies
WORKDIR /app/meeting_summary

# Install any dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Install debugpy for remote debugging
RUN pip install debugpy

# Inform Docker that the container is listening on the specified port at runtime.
EXPOSE 8501

# Expose the debug port, 5678 is the default for debugpy
EXPOSE 5678

# Set an environment variable to determine the mode
ENV DEBUG_MODE=false

# Command to run the application, conditionally based on DEBUG_MODE
CMD if [ "$DEBUG_MODE" = "true" ]; then tail -f /dev/null; else streamlit run app.py; fi