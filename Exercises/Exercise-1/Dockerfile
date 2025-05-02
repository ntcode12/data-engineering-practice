FROM python:latest

WORKDIR /app
COPY requirements.txt .
COPY . /app

RUN pip install --no-cache-dir -r requirements.txt
RUN python3 -m pip install -r requirements.txt

CMD ["python3", "main.py"]
