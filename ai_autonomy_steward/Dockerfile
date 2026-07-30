FROM ghcr.io/home-assistant/base:latest

RUN apk add --no-cache python3 py3-pip
RUN pip install --no-cache-dir --break-system-packages aiohttp pyyaml

COPY ai_autonomy_steward.py /ai_autonomy_steward.py
COPY constraint_layer.py /constraint_layer.py
COPY run.sh /run.sh
RUN chmod a+x /run.sh

CMD [ "/run.sh" ]
