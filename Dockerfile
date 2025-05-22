FROM python:3.13-slim

WORKDIR /app

COPY requirements.txt requirements.txt
RUN pip3 install --upgrade --no-cache-dir -r requirements.txt

COPY app.py app.py
RUN export FLASK_APP=app

CMD [ "python3", "-m" , "flask", "run", "--host=0.0.0.0"]