FROM --platform=linux/amd64 python:3.10-slim

WORKDIR /app

COPY app/requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

COPY app .

CMD ["python", "process_pdfs.py"]
