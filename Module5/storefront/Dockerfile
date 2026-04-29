FROM nginx:alpine

# Xoá giao diện mặc định của nginx
RUN rm -rf /usr/share/nginx/html/*

# Copy file index.html của storefront vào
COPY index.html /usr/share/nginx/html/

# Phục vụ file ở cổng 80 (bên trong container)
EXPOSE 80
CMD ["nginx", "-g", "daemon off;"]
