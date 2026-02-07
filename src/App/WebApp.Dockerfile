FROM node:20-alpine AS build
WORKDIR /home/node/app

COPY ./package*.json ./

RUN npm ci --omit=dev

COPY . .

RUN npm run build

FROM nginx:alpine

COPY --from=build /home/node/app/build /usr/share/nginx/html

COPY public/startup.sh /usr/share/nginx/html/startup.sh
RUN chmod +x /usr/share/nginx/html/startup.sh && sed -i 's/\r$//' /usr/share/nginx/html/startup.sh

# Expose the application port (nginx default)
EXPOSE 80

# Health check to verify nginx is serving content
HEALTHCHECK --interval=30s --timeout=10s --start-period=10s --retries=3 \
    CMD wget --no-verbose --tries=1 --spider http://localhost:80/ || exit 1

# Run startup script instead of nginx directly
CMD ["/bin/sh", "/usr/share/nginx/html/startup.sh"]
