FROM python:3.9-slim

# Set up working directory
WORKDIR /app

# Copy the requirements file and install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy the entire project code into the container
COPY . .

# Expose port (Hugging Face Docker spaces expect port 7860 by default)
ENV PORT=7860
ENV WEB_SERVER_BIND_ADDRESS="0.0.0.0"
EXPOSE 7860

# Run the stream bot
CMD ["python", "-m", "WebStreamer"]
