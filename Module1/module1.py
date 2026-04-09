import pandas as pd
import mysql.connector
import os
import time
import shutil
from datetime import datetime

# =========================
# CẤU HÌNH THƯ MỤC
# =========================
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
INPUT_DIR = os.path.join(BASE_DIR, "input_data")
PROCESSED_DIR = os.path.join(BASE_DIR, "processed_data")
ERROR_DIR = os.path.join(BASE_DIR, "error_data")
CLEANED_DIR = os.path.join(BASE_DIR, "cleaned_data")  # Thư mục mới chứa Data sạch

# Tự động tạo thư mục nếu chưa có
for folder in [INPUT_DIR, PROCESSED_DIR, ERROR_DIR, CLEANED_DIR]:
    os.makedirs(folder, exist_ok=True)

# =========================
# 1. XỬ LÝ FILE CSV (RESILIENCE)
# =========================
def process_inventory(file_path):
    print(f"\n[+] Đang xử lý file: {file_path}")
    try:
        df = pd.read_csv(file_path)
        
        # Ép kiểu cột quantity về số, lỗi (chữ) biến thành NaN
        df['quantity'] = pd.to_numeric(df['quantity'], errors='coerce')
        
        # Phân loại dữ liệu Hợp lệ (>= 0) và Không hợp lệ
        valid_df = df[(df['quantity'] >= 0) & (df['quantity'].notna())]
        invalid_df = df[~df.index.isin(valid_df.index)]
        
        # Groupby dữ liệu hợp lệ để tránh trùng lặp
        inventory_to_update = valid_df.groupby('product_id')['quantity'].sum().reset_index()
        
        # Lưu vết dữ liệu lỗi (nếu có)
        if not invalid_df.empty:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            error_file = os.path.join(ERROR_DIR, f"error_log_{timestamp}.csv")
            invalid_df.to_csv(error_file, index=False)
            print(f"⚠️ Phát hiện {len(invalid_df)} dòng lỗi. Đã lưu log tại: {error_file}")
            
        return inventory_to_update

    except Exception as e:
        print(f"❌ Lỗi khi đọc/xử lý file CSV: {e}")
        return None

# =========================
# 2. CẬP NHẬT DATABASE (CÓ CƠ CHẾ RETRY CONNECTION)
# =========================
def update_database(inventory):
    conn = None
    cursor = None
    max_retries = 5  # Thử tối đa 5 lần
    retry_delay = 5  # Đợi 5 giây giữa mỗi lần thử

    for attempt in range(max_retries):
        try:
            print(f"[*] Đang kết nối Database (Lần {attempt + 1}/{max_retries})...")
            # Kết nối lấy thông tin qua biến môi trường
            conn = mysql.connector.connect(
                host=os.getenv("DB_HOST", "localhost"),
                user=os.getenv("DB_USER", "root"),
                password=os.getenv("DB_PASSWORD", "123456"),
                database=os.getenv("DB_NAME", "inventory_management")
            )
            cursor = conn.cursor()
            print("✅ Kết nối Database thành công!")
            
            for _, row in inventory.iterrows():
                try:
                    cursor.execute("""
                        UPDATE products
                        SET stock = %s
                        WHERE id = %s
                    """, (int(row['quantity']), int(row['product_id'])))
                except Exception as e:
                    print(f"⚠️ Lỗi update product_id {row['product_id']}: {e}")
                    continue
                    
            conn.commit()
            print("✅ Cập nhật dữ liệu vào DB thành công!")
            return True

        except mysql.connector.Error as err:
            print(f"❌ Lỗi kết nối DB: {err}")
            if attempt < max_retries - 1:
                print(f"⏳ Đang thử lại sau {retry_delay} giây...")
                time.sleep(retry_delay)
            else:
                print("🛑 Đã thử hết số lần. Bỏ cuộc!")
                return False
        finally:
            if cursor: cursor.close()
            if conn: conn.close()

# =========================
# 3. EXPORT DỮ LIỆU SẠCH
# =========================
def export_cleaned_data(inventory, original_filename):
    try:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        cleaned_filename = f"cleaned_{timestamp}_{original_filename}"
        output_path = os.path.join(CLEANED_DIR, cleaned_filename)
        
        inventory.to_csv(output_path, index=False, encoding="utf-8-sig")
        print(f"📁 Đã xuất file CSV dữ liệu sạch: {output_path}")
    except Exception as e:
        print(f"❌ Lỗi export file sạch: {e}")

# =========================
# 4. WATCHDOG SERVICE (POLLING)
# =========================
def watch_and_process():
    print(f"👁️ Watchdog đang chạy... Đang giám sát thư mục: {INPUT_DIR}")
    print("Nhấn Ctrl+C để dừng.\n")
    
    while True:
        try:
            for filename in os.listdir(INPUT_DIR):
                if filename.endswith(".csv"):
                    file_path = os.path.join(INPUT_DIR, filename)
                    
                    # 1. Đọc và làm sạch dữ liệu
                    inventory_data = process_inventory(file_path)
                    
                    if inventory_data is not None and not inventory_data.empty:
                        # 2. Cập nhật Database
                        db_success = update_database(inventory_data)
                        
                        if db_success:
                            # 3. Xuất file dữ liệu sạch
                            export_cleaned_data(inventory_data, filename)
                            
                            # 4. Di chuyển file RAW gốc đi cất
                            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                            processed_filename = f"processed_{timestamp}_{filename}"
                            dest_path = os.path.join(PROCESSED_DIR, processed_filename)
                            shutil.move(file_path, dest_path)
                            print(f"✅ Đã di chuyển file gốc RAW sang: {PROCESSED_DIR}")
                        else:
                            print("❌ Cập nhật DB thất bại, giữ nguyên file để thử lại sau.")
                    else:
                        print("⚠️ File trống hoặc không có dữ liệu hợp lệ. Đã bỏ qua.")
                        os.remove(file_path) 
            
            time.sleep(5)
            
        except KeyboardInterrupt:
            print("\n🛑 Đã dừng Watchdog Service.")
            break
        except Exception as e:
            print(f"❌ Lỗi hệ thống Watchdog: {e}")
            time.sleep(5)

# =========================
# MAIN ENTRY POINT
# =========================
if __name__ == "__main__":
    watch_and_process()