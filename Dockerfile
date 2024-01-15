# Use the official Python image as a parent image
FROM python:3.11.6-slim

# Set the working directory in the container
WORKDIR /app

# Install ffmpeg and git
RUN apt-get update && \
    apt-get install -y ffmpeg git && \
    apt-get clean && \
    rm -rf /var/lib/apt/lists/*

# Allow user to specify the branch to clone
ARG BRANCH=main
RUN git clone -b $BRANCH https://github.com/ashutoshdhanda/meeting_summary.git

# Set the working directory for installing python dependencies
WORKDIR /app/meeting_summary

# Install dependencies conditionally based on DEBUG_MODE
ARG DEBUG_MODE=false
RUN if [ "$DEBUG_MODE" = "true" ]; then \
        pip install --no-cache-dir -r requirements-dev.txt; \
    else \
        pip install --no-cache-dir -r requirements.txt; \
    fi

# Inform Docker that the container is listening on the specified port at runtime.
EXPOSE 8501

# Expose the debug port, 5678 is the default for debugpy
EXPOSE 5678

# Command to run the application, conditionally based on DEBUG_MODE
CMD if [ "$DEBUG_MODE" = "true" ]; then tail -f /dev/null; else streamlit run app.py; fi
