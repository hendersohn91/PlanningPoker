FROM node:22-alpine

ARG http_proxy
ARG https_proxy

RUN corepack enable && corepack prepare pnpm@latest --activate

WORKDIR /app/PlanningPoker
COPY package.json pnpm-lock.yaml* ./
RUN pnpm install --frozen-lockfile --prod
COPY . .

ENTRYPOINT ["pnpm", "start"]
