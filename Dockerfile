FROM python:alpine AS pycurl

RUN apk add -u --no-cache libcurl libstdc++ && \
    apk add -u --no-cache --virtual .build-deps build-base g++ libffi-dev curl-dev && \
    pip install --no-cache-dir pycurl

FROM python:alpine AS app
WORKDIR /app
COPY --from=pycurl /usr/local/lib/python3.10/site-packages/pycurl* /usr/local/lib/python3.10/site-packages/
COPY ./webex/ ./
RUN apk add libcurl curl && pip install Flask  python-json-logger
CMD ["python","/app/webex.py"]