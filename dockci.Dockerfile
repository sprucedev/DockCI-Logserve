FROM debian:jessie

ENV DEBIAN_FRONTEND noninteractive
RUN apt-get update && apt-get install -y \
        git \
        python3 python3-dev python3-setuptools
RUN easy_install3 pip wheel virtualenv

RUN mkdir -p /code/data
WORKDIR /code

ADD requirements.txt /code/requirements.txt
ADD test-requirements.txt /code/test-requirements.txt
ADD util/wheelhouse /code/wheelhouse
ADD _deps_python.sh /code/_deps_python.sh
RUN ./_deps_python.sh

ADD entrypoint.sh /code/entrypoint.sh
ADD dockci /code/dockci
ADD tests /code/tests
ADD pylint.conf /code/pylint.conf

EXPOSE 5000
ENTRYPOINT ["/code/entrypoint.sh"]
CMD ["run"]
