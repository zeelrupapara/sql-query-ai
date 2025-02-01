FROM python:3.8-slim

# Set the working directory in the container
WORKDIR /app

# Copy the application files to the container
COPY . /app

# Install system dependencies
RUN apt-get update && \
    apt-get install -y --no-install-recommends libsqlite3-dev && \
    rm -rf /var/lib/apt/lists/*

# Create a virtual environment and install dependencies
RUN python -m venv venv && \
    . venv/bin/activate && \
    pip install --no-cache-dir -r requirements.txt

# Expose the port Streamlit runs on
EXPOSE 8501

# Set environment variables
ENV OPENAI_API_KEY="your_api_key_here"
ENV PATH="/app/venv/bin:$PATH"
ENV GEMINI_API_KEY=AIzaSyAtr0-4q5tGeoWFCqw6P6zrtGDr9SPXA8A

# Command to run the application
CMD ["streamlit", "run", "streamlit_app.py"]
