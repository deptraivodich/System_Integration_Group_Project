FROM python:3.9-slim

WORKDIR /app

# Tạo thư mục cần thiết
RUN mkdir -p input_data processed_data error_data cleaned_data

# Cài thư viện
RUN pip install --no-cache-dir pandas mysql-connector-python

# Copy source code
COPY module1.py .

CMD ["python", "module1.py"]
