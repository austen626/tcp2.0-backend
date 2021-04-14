# pull official base image
FROM python

# set work directory
WORKDIR /usr/src/app

# set environment variables
ENV PYTHONDONTWRITEBYTECODE 1
ENV PYTHONUNBUFFERED 1

# install dependencies
RUN pip install --upgrade pip
COPY ./requirements.txt .
RUN pip install -r requirements.txt
# copy project
COPY . /usr/src/app/
# run development server
CMD python /usr/src/app/manage.py makemigrations
CMD python /usr/src/app/manage.py migrate
CMD python /usr/src/app/manage.py runserver 0.0.0.0:$PORT
