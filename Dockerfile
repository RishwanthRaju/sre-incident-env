FROM python:3.11-slim
WORKDIR /app
COPY . /app
RUN pip install fastapi uvicorn httpx openai pydantic requests
EXPOSE 7860
CMD ["uvicorn", "server.app:app", "--host", "0.0.0.0", "--port", "7860"]