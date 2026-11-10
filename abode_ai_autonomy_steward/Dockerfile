FROM ghcr.io/home-assistant/base:latest

RUN apk add --no-cache python3 py3-pip
RUN pip install --no-cache-dir --break-system-packages aiohttp pyyaml

COPY abode_ai_autonomy_steward.py /abode_ai_autonomy_steward.py
COPY constraint_layer.py /constraint_layer.py
COPY decision_log.py /decision_log.py
COPY charter.py /charter.py
COPY charter.md /charter.md
COPY constraints.yaml /constraints.yaml
COPY run.sh /run.sh
RUN chmod a+x /run.sh

CMD [ "/run.sh" ]
