# Use a lightweight Python base image
FROM python:3.12-slim

# Set the working directory in the container
WORKDIR /app

# The dashboard and comparison tools only use Python's standard library.
# No requirements.txt needed at this stage.

# Copy the dashboard and server files
# We only copy the essentials; the rest can be mounted via docker-compose for real-time updates.
COPY serve_dashboard.py .
COPY oai_dashboard.html .
COPY compare_oai.py .
COPY README.md .

# Create an empty results file so the server doesn't 404 on first load
RUN touch comparison_results.txt

# Expose the dashboard port
EXPOSE 8080

# Start the dashboard server by default
CMD ["python", "serve_dashboard.py"]
