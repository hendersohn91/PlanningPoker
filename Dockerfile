FROM node:22-alpine

ARG http_proxy
ARG https_proxy

WORKDIR /app/PlanningPoker
COPY . .
RUN npm install --omit=dev

ENTRYPOINT ["npm", "start"]
