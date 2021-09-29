# syntax=docker/dockerfile:1

FROM rackspacedot/python37:latest
RUN git clone https://github.com/brandonscript/fylm.git
RUN cd fylm; git pull
RUN pip3 install -r fylm/requirements.txt
COPY . .
ENTRYPOINT ["python","fylm/fylm"]