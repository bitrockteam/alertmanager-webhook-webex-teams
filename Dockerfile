FROM python:alpine
WORKDIR /app
RUN pip install Flask  python-json-logger requests
COPY ./webex/ ./
CMD ["python","/app/webex.py"]
