FROM python:3.12-slim
WORKDIR /srv/spes
COPY app ./app
COPY backend ./backend
COPY mobile ./mobile
RUN pip install --no-cache-dir -r backend/requirements.txt
ENV PYTHONPATH=/srv/spes/app
ENV SPES_API_DB=/srv/spes/data/consolle_spes_server.db
EXPOSE 8000
CMD ["sh", "-c", "uvicorn backend.main:app --host 0.0.0.0 --port ${PORT:-8000} --proxy-headers"]
