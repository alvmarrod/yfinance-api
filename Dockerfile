FROM python:3.13-slim

WORKDIR /app

COPY requirements.txt requirements.txt
RUN pip3 install --upgrade --no-cache-dir -r requirements.txt

COPY . .

RUN mkdir -p cache

EXPOSE 5000

CMD [ "python3", "-m", "flask", "run", "--host=0.0.0.0" ]
