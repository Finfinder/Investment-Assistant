ARG NGINX_VERSION=1.27-alpine
# IA-167: wersja bazowego obrazu nginx z pliku single-source-of-truth nginx/.nginxrc.
ARG NGINX_IMAGE_DIGEST="sha256:65645c7bb6a0661892a8b03b89d0743208a18dd2f3f17a54ef4b76fb8e2f2a10"
# IA-164: digest listy manifestów oficjalnego nginx:${NGINX_VERSION}.
# UWAGA: digest jest scisle sprzezony z NGINX_VERSION - przy zmianie ARG powyzej nalezy
# zaktualizowac tez ten digest (obraz bazowy innego tagu ma inny digest).
# Rotacja: docker buildx imagetools inspect nginx:$(cat nginx/.nginxrc) (pole "Digest:").
# Zmieniaj razem z nginx/.nginxrc - digest jest autorytatywny (content-addressing), wiec tag
# jest tylko wskazowka; bez rotacji digestu obraz pozostanie na starym nginx mimo zmiany .nginxrc.
FROM nginx:${NGINX_VERSION}@${NGINX_IMAGE_DIGEST}

COPY nginx.conf /etc/nginx/conf.d/default.conf

EXPOSE 80
