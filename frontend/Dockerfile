# syntax=docker/dockerfile:1

# ---- build ----------------------------------------------------------------
FROM node:20-slim AS build

WORKDIR /app

# Vite inlines VITE_* vars at build time, so they must be present now.
# Pass with: docker build --build-arg VITE_API_URL=... --build-arg VITE_SUPABASE_URL=... ...
ARG VITE_API_URL
ARG VITE_SUPABASE_URL
ARG VITE_SUPABASE_ANON_KEY
ENV VITE_API_URL=$VITE_API_URL \
    VITE_SUPABASE_URL=$VITE_SUPABASE_URL \
    VITE_SUPABASE_ANON_KEY=$VITE_SUPABASE_ANON_KEY

COPY package.json package-lock.json ./
RUN npm ci

COPY . .
RUN npm run build

# ---- serve --------------------------------------------------------------
FROM nginx:1.27-alpine AS serve

COPY nginx.conf /etc/nginx/conf.d/default.conf
COPY --from=build /app/dist /usr/share/nginx/html

EXPOSE 80

CMD ["nginx", "-g", "daemon off;"]
