ARG NGINX_IMAGE_DIGEST="sha256:65645c7bb6a0661892a8b03b89d0743208a18dd2f3f17a54ef4b76fb8e2f2a10"
# IA-164: digest listy manifestów oficjalnego nginx:1.27-alpine.
# Rotacja: docker buildx imagetools inspect nginx:1.27-alpine (pole "Digest:").
FROM nginx:1.27-alpine@${NGINX_IMAGE_DIGEST}

COPY nginx.conf /etc/nginx/conf.d/default.conf

EXPOSE 80
