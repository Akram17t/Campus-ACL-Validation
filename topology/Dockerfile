FROM debian:trixie-20261027-slim

RUN apt-get update \
    && apt-get install -y --no-install-recommends \
        conntrack iproute2 iputils-ping nftables \
    && rm -rf /var/lib/apt/lists/*

CMD ["sleep", "infinity"]
