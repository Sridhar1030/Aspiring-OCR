#!/bin/bash
# Install Tesseract OCR
apt-get update && apt-get install -y tesseract-ocr
# Start the FastAPI application
uvicorn main:app --host 0.0.0.0 --port 8000
