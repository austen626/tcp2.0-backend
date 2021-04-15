# pull official base image
FROM python

# set work directory
WORKDIR /usr/src/app

# set environment variables
ENV PYTHONDONTWRITEBYTECODE 1
ENV PYTHONUNBUFFERED 1

RUN apt-get update && apt-get install -y net-tools wget unzip && \
    bash && \
  # ENABLE GCLOUD SDK IF NEEDED
  # curl -sSL https://sdk.cloud.google.com | bash && \
 
  # DOWNLOAD AND INSTALL CLOUD SQL PROXY
  wget https://dl.google.com/cloudsql/cloud_sql_proxy.linux.amd64 -O /usr/local/bin/cloud_sql_proxy && \  
  chmod +x /usr/local/bin/cloud_sql_proxy && \
  chmod +x /usr/local/bin/cloud-run-entrypoint.sh

# install dependencies
RUN pip install --upgrade pip
COPY ./requirements.txt .
RUN pip install -r requirements.txt
# copy project
COPY . /usr/src/app/

ENTRYPOINT ["cloud-run-entrypoint.sh"]

# run development server
CMD python /usr/src/app/manage.py makemigrations
CMD python /usr/src/app/manage.py migrate
CMD python /usr/src/app/manage.py runserver 0.0.0.0:$PORT
