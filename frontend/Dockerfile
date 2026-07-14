# syntax=docker/dockerfile:1
ARG NODE_VERSION=20
# IA-163: digest listy manifestow (index digest) oficjalnego node:${NODE_VERSION}-alpine.
# Rotacja: docker buildx imagetools inspect node:$(cat frontend/.nvmrc)-alpine (pole "Digest:").
# Zmieniaj razem z frontend/.nvmrc - digest jest autorytatywny (content-addressing), wiec tag
# jest tylko wskazowka; bez rotacji digestu obraz pozostanie na starym Node mimo zmiany .nvmrc.
ARG NODE_IMAGE_DIGEST="sha256:fb4cd12c85ee03686f6af5362a0b0d56d50c58a04632e6c0fb8363f609372293"
FROM node:${NODE_VERSION}-alpine@${NODE_IMAGE_DIGEST} AS builder

WORKDIR /app
COPY package.json package-lock.json .npmrc ./
RUN --mount=type=cache,target=/root/.npm,id=frontend-npm npm ci
COPY . .

ARG NEXT_PUBLIC_API_URL
ARG NEXT_PUBLIC_WS_URL
ENV NEXT_PUBLIC_API_URL=$NEXT_PUBLIC_API_URL
ENV NEXT_PUBLIC_WS_URL=$NEXT_PUBLIC_WS_URL

RUN npm run build

FROM node:${NODE_VERSION}-alpine@${NODE_IMAGE_DIGEST} AS runner
WORKDIR /app
ENV NODE_ENV=production
ENV HOSTNAME=0.0.0.0

RUN addgroup --system --gid 1001 nodejs && adduser --system --uid 1001 nextjs

COPY --from=builder /app/.next/standalone ./
COPY --from=builder /app/.next/static ./.next/static

USER nextjs
EXPOSE 3000
CMD ["node", "server.js"]
