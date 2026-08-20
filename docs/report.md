# **Báo Cáo Kỹ Thuật - Giai Đoạn 2**
### **Team Members:**
*   **Hoang Nguyen The Hien** - Student ID: 25127326
*   **Phan Quoc Bao** - Student ID: 25127282
*   **Luu Minh Tien** - Student ID: 25127242

## **1. Mô tả kiến trúc hệ thống**

Hệ thống được nâng cấp và tái thiết kế theo mô hình Bất đồng bộ (Asynchronous Non-blocking I/O) nhằm giải quyết bài toán xử lý đồng thời hiệu suất cao.

- **Mô hình cốt lõi:** Sử dụng thư viện `asyncio` của Python với kiến trúc Event-Driven. Thay vì mỗi Client chiếm dụng một Thread riêng (gây tốn kém bộ nhớ như ở Giai đoạn 1), toàn bộ Client giờ đây được phục vụ song song trên một Event Loop duy nhất.
- **Offload Blocking I/O:** Để tránh việc đọc/ghi file hoặc tính toán MD5 làm đóng băng Event Loop, các tác vụ nặng (Disk I/O, CPU-bound) được đẩy sang một Thread Pool riêng biệt thông qua hàm `run_in_executor`.
- **Cơ chế giới hạn kết nối:** Sử dụng `asyncio.Semaphore(MAX_CLIENTS)` hoạt động như một chốt chặn ở tầng trên cùng, lập tức từ chối các kết nối dôi dư nhằm bảo vệ máy chủ không bị quá tải.


## **2. Đặc tả giao thức tùy chỉnh**

Giao thức được chuyển đổi hoàn toàn từ văn bản sang dạng Nhị phân để tối ưu băng thông và tốc độ xử lý.

- **Cấu trúc gói tin:** Mọi thông điệp giao tiếp đều tuân thủ quy tắc đóng gói Header 8 byte cố định `[Length: 4 byte] [Opcode: 2 byte] [UserID: 2 byte] [Payload: ... byte]`.
- **Network Byte Order:** Tất cả các tham số số nguyên được đóng gói bằng thư viện `struct` với chuẩn Big-Endian (`!IHH`) để đảm bảo tính nhất quán trên đa nền tảng.
- **Tách bạch dữ liệu và điều khiển:** Các thao tác truyền file được chia nhỏ thành các gói `FILE_CHUNK` (Mặc định 16KB). Các lệnh điều khiển như `ACK`, `CHECKSUM_REQ`, `ERROR` được sử dụng để duy trì tính đồng bộ của State Machine giữa Client và Server.

### **2.1 Cấu trúc gói tin Chung (Header)**
Mọi gói tin truyền đi trong Giai đoạn 2 đều tuân theo một Header cố định dài 8 byte, cấu trúc như sau:

| Field | Size (Bytes) | Type | Mô tả |
| --- | --- | --- | --- |
| `Length` | 4 | Unsigned Int (`!I`) | Kích thước của phần Payload (không tính Header). Có thể lên tới 4GB. |
| `Opcode` | 2 | Unsigned Short (`!H`) | Mã lệnh định danh loại hành động. |
| `UserID` | 2 | Unsigned Short (`!H`) | Mã định danh client/user. (0 = Chưa đăng nhập). |

*Tất cả các số nguyên đều được đóng gói theo Network Byte Order (Big-Endian) sử dụng dấu `!` trong thư viện `struct`.*

### **2.2 Bảng Opcode**

| Opcode (Dec) | Opcode (Hex) | Tên lệnh | Hướng | Ý nghĩa |
| --- | --- | --- | --- | --- |
| 1 | `0x0001` | `LOGIN` | C -> S | Client đăng nhập kèm username. |
| 2 | `0x0002` | `LIST_REQ` | C -> S | Yêu cầu danh sách file trong thư mục cá nhân. |
| 3 | `0x0003` | `LIST_RESP` | S -> C | Trả về danh sách file (chuỗi cách nhau dấu phẩy). |
| 4 | `0x0004` | `UPLOAD_REQ` | C -> S | Yêu cầu tải file lên. Payload chứa thông tin file. |
| 5 | `0x0005` | `DOWNLOAD_REQ`| C -> S | Yêu cầu tải file về. Payload chứa tên file. |
| 6 | `0x0006` | `FILE_CHUNK` | C <-> S | Chứa dữ liệu thực sự của file. |
| 7 | `0x0007` | `CHECKSUM_REQ`| C -> S | Client gửi mã băm để verify sau khi UPLOAD. |
| 8 | `0x0008` | `CHECKSUM_RESP`| S -> C | Server trả mã băm cho client sau khi DOWNLOAD. |
| 9 | `0x0009` | `ACK` | S -> C | Trả về phản hồi thành công (có thể kèm dữ liệu như `next_offset`). |
| 10 | `0x000A` | `ERROR` | S -> C | Báo lỗi. Payload là chuỗi lý do lỗi. |

### **2.3 Cấu trúc Payload theo từng Opcode**

#### **2.3.1 `LOGIN` (0x01)**
- **Payload**: Chuỗi UTF-8 tên username (ví dụ: `Alice`).

#### **2.3.2 `LIST_REQ` (0x02)**
- **Payload**: Trống (0 bytes).

#### **2.3.3 `LIST_RESP` (0x03)**
- **Payload**: Chuỗi UTF-8 danh sách file, cách nhau dấu phẩy. Ví dụ: `file1.txt,file2.zip`.

#### **2.3.4 `UPLOAD_REQ` (0x04)**
- Dùng cho cả gửi mới và Resume (truyền tiếp).
- **Payload Format**: `[Kích thước file: 8 byte (!Q)] [Tên file: chuỗi UTF-8 còn lại]`

#### **2.3.5 `ACK` (0x09) trả lời cho `UPLOAD_REQ`**
- Server kiểm tra file trên đĩa, nếu file đã tồn tại và chưa đủ dung lượng, server trả về offset hiện tại để client resume.
- **Payload Format**: `[next_offset: 8 byte (!Q)]`
- Nếu file chưa tồn tại (tải mới), `next_offset` = 0.

#### **2.3.6 `DOWNLOAD_REQ` (0x05)**
- **Payload Format**: `[offset hiện có ở client: 8 byte (!Q)] [Tên file: chuỗi UTF-8 còn lại]`
- Client truyền `offset` lên để báo cho Server biết nó đang có bao nhiêu byte, Server sẽ chỉ gửi từ `offset` đó trở đi (Resume Download).

#### **2.3.7 `FILE_CHUNK` (0x06)**
- **Payload**: Dữ liệu thô của file (bytes). 

#### **2.3.8 `ERROR` (0x0A)**
- **Payload**: Chuỗi UTF-8 báo lỗi. (VD: `INVALID_FILE`, `MAX_CLIENTS_REACHED`).

### **2.4 Ví dụ luồng truyền tiếp (Resume)**
1. Client gửi `UPLOAD_REQ` (Payload: `8 byte size` + `"video.mp4"`).
2. Server check `storage/user/video.mp4`, nhận thấy có sẵn 10MB (10485760 bytes).
3. Server gửi lại `ACK` (Payload: `10485760` đóng gói 8 byte).
4. Client nhận được `ACK`, đọc file từ byte thứ 10485760.
5. Client liên tục gửi `FILE_CHUNK` đến khi hết file.

### **2.5 Ví dụ Hex Dump thực tế (Gói tin LOGIN)**

Giả sử Client gửi lệnh **LOGIN** với Username là `"Alice"` (`5` bytes). Client có `UserID` tạm thời là `0`.
- **Length**: 5 bytes (0x00 00 00 05)
- **Opcode**: 1 (0x00 01)
- **UserID**: 0 (0x00 00)
- **Payload**: "Alice" (0x41 0x6C 0x69 0x63 0x65)

**Hex Dump toàn bộ gói tin (13 bytes):**
```text
00 00 00 05 00 01 00 00 41 6C 69 63 65
|----Length---|--Op-|-ID--|--Payload---|
```
- `00 00 00 05`: 4 byte Header mô tả Length = 5.
- `00 01`: 2 byte Header mô tả Opcode = 1 (LOGIN).
- `00 00`: 2 byte Header mô tả UserID = 0.
- `41 6c 69 63 65`: 5 byte Payload chứa chuỗi ASCII "Alice".


## **3. Các lựa chọn kỹ thuật quan trọng**

### **3.1. Thuật toán Token Bucket (Giới hạn băng thông)**
- Để đáp ứng tiêu chí R2.6, nhóm đã thiết kế class `TokenBucket` giới hạn tốc độ luồng dữ liệu truyền tải theo cấu hình `SPEED_LIMIT_KBPS` (500 KB/s). Việc giới hạn được thực thi bằng cách tính toán thời gian `time.monotonic()` và `asyncio.sleep()` tương ứng với số byte được gửi, giúp tốc độ truyền duy trì ổn định, không vượt quá ngưỡng cấu hình +/- 10%.

### **3.2. Không gian lưu trữ độc lập**
- Để tránh Race Condition khi nhiều user thao tác cùng lúc (R2.3), mọi dữ liệu tải lên được điều hướng lưu trữ độc lập theo đường dẫn `storage/<username>/<filename>`. Việc này ngăn chặn triệt để hiện tượng ghi đè chéo hoặc lộ lọt dữ liệu giữa các người dùng.
- Chính sách trùng tên: Nếu một User upload file trùng tên đã có sẵn nhưng kích thước file cũ lớn hơn hoặc bằng, hệ thống tự động áp dụng chính sách ghi đè, xóa file cũ để tải file mới.

### **3.3. Cơ chế truyền tiếp (Offset-based resume)**
- Hệ thống hỗ trợ Resume cho cả 2 chiều Upload và Download. Khi một kết nối bị ngắt giữa chừng, Client hoặc Server sẽ kiểm tra dung lượng file đang tải dở trên đĩa cứng và đóng gói kích thước này (Offset) vào gói tin `UPLOAD_REQ` hoặc `ACK`. Phía còn lại sẽ thực hiện hành động nhảy (Seek) tới đúng offset tương ứng để bắt đầu đọc/ghi từ byte đó trở đi, tiết kiệm 100% tài nguyên mạng dư thừa.

### **3.4. Cấu hình động & Nhật ký (Logging) chi tiết**
- **Cấu hình động:** Hệ thống hỗ trợ thay đổi cấu hình linh hoạt thông qua Biến môi trường (Environment Variables) hoặc Cờ lệnh (CLI Flags). Thay vì phải sửa mã nguồn, quản trị viên có thể dễ dàng khởi động hệ thống với cấu hình mới ngay trên Terminal (Ví dụ: `py src/server.py --port 9090 --speed 1000`). Điều này giúp việc triển khai qua các Tunnel (như Ngrok, Playit, Radmin VPN) trở nên cực kỳ tiện lợi.
- **Nhật ký truy vết (Audit Logging):** Mọi thao tác truyền tải file đều được Server ghi nhận lại chi tiết bao gồm cả Địa chỉ IP và Tên đăng nhập (Username) của người dùng. Việc này giúp dễ dàng quản lý và giám sát trực quan (Ví dụ: `[127.0.0.1:41235 | hoang_dz] Start UPLOAD phim.mp4...`).


## **4. Kết quả kiểm thử**

### **4.1. Bài kiểm tra độ ổn định & xử lý đa luồng**
- **Kịch bản:** Chạy script `tests/simulate_multi_client.py` với 10 Client ảo đồng loạt kết nối, đăng nhập và xả dữ liệu dồn dập vào Server.
- **Kết quả:**
  - 10 Client xử lý thành công không xảy ra Deadlock.
  
```text
server:
2026-08-18 07:42:33,714 [INFO] - Connected to ('127.0.0.1', 52076)
2026-08-18 07:42:33,715 [INFO] - Connected to ('127.0.0.1', 52077)
2026-08-18 07:42:33,717 [INFO] - Connected to ('127.0.0.1', 52078)
2026-08-18 07:42:33,717 [INFO] - Connected to ('127.0.0.1', 52079)
2026-08-18 07:42:33,718 [INFO] - Connected to ('127.0.0.1', 52080)
2026-08-18 07:42:33,720 [INFO] - Connected to ('127.0.0.1', 52081)
2026-08-18 07:42:33,721 [INFO] - Connected to ('127.0.0.1', 52082)
2026-08-18 07:42:33,722 [INFO] - Connected to ('127.0.0.1', 52083)
2026-08-18 07:42:33,722 [INFO] - Connected to ('127.0.0.1', 52084)
2026-08-18 07:42:33,723 [INFO] - Connected to ('127.0.0.1', 52085)
2026-08-18 07:42:33,724 [INFO] - [('127.0.0.1', 52078)] LOGIN success as 'bot_3'
2026-08-18 07:42:33,726 [INFO] - [('127.0.0.1', 52077)] LOGIN success as 'bot_2'
2026-08-18 07:42:33,727 [INFO] - [('127.0.0.1', 52079)] LOGIN success as 'bot_4'
2026-08-18 07:42:33,729 [INFO] - [('127.0.0.1', 52080)] LOGIN success as 'bot_5'
2026-08-18 07:42:33,729 [INFO] - [('127.0.0.1', 52083)] LOGIN success as 'bot_8'
2026-08-18 07:42:33,730 [INFO] - [('127.0.0.1', 52084)] LOGIN success as 'bot_9'
2026-08-18 07:42:33,730 [INFO] - [('127.0.0.1', 52085)] LOGIN success as 'bot_10'
2026-08-18 07:42:33,731 [INFO] - [('127.0.0.1', 52076)] LOGIN success as 'bot_1'
2026-08-18 07:42:33,736 [INFO] - [('127.0.0.1', 52082)] LOGIN success as 'bot_7'
2026-08-18 07:42:33,737 [INFO] - [('127.0.0.1', 52081)] LOGIN success as 'bot_6'
2026-08-18 07:42:33,876 [INFO] - [('127.0.0.1', 52082) | bot_7] Overwrite existing dummy_7.bin
2026-08-18 07:42:33,877 [INFO] - [('127.0.0.1', 52082) | bot_7] Start UPLOAD dummy_7.bin (18444 bytes)
2026-08-18 07:42:33,879 [INFO] - [('127.0.0.1', 52082) | bot_7] UPLOAD dummy_7.bin completed. Session avg speed: 11486.49 KB/s
2026-08-18 07:42:33,900 [INFO] - Disconnected from ('127.0.0.1', 52082)
2026-08-18 07:42:33,925 [INFO] - [('127.0.0.1', 52081) | bot_6] Resume UPLOAD dummy_6.bin from 1552/40297
2026-08-18 07:42:33,927 [INFO] - [('127.0.0.1', 52081) | bot_6] UPLOAD dummy_6.bin completed. Session avg speed: 27904.74 KB/s
2026-08-18 07:42:33,940 [INFO] - Disconnected from ('127.0.0.1', 52081)
2026-08-18 07:42:33,950 [INFO] - [('127.0.0.1', 52078) | bot_3] Overwrite existing dummy_3.bin
2026-08-18 07:42:33,952 [INFO] - [('127.0.0.1', 52078) | bot_3] Start UPLOAD dummy_3.bin (14862 bytes)
2026-08-18 07:42:33,954 [INFO] - [('127.0.0.1', 52078) | bot_3] UPLOAD dummy_3.bin completed. Session avg speed: 9169.27 KB/s
2026-08-18 07:42:33,972 [INFO] - Disconnected from ('127.0.0.1', 52078)
2026-08-18 07:42:33,996 [INFO] - [('127.0.0.1', 52085) | bot_10] Start UPLOAD dummy_10.bin (38515 bytes)
2026-08-18 07:42:34,001 [INFO] - [('127.0.0.1', 52085) | bot_10] UPLOAD dummy_10.bin completed. Session avg speed: 18490.09 KB/s
2026-08-18 07:42:34,015 [INFO] - Disconnected from ('127.0.0.1', 52085)
2026-08-18 07:42:34,086 [INFO] - [('127.0.0.1', 52079) | bot_4] Resume UPLOAD dummy_4.bin from 35296/43965
2026-08-18 07:42:34,089 [INFO] - [('127.0.0.1', 52079) | bot_4] UPLOAD dummy_4.bin completed. Session avg speed: 26117.57 KB/s
2026-08-18 07:42:34,101 [INFO] - Disconnected from ('127.0.0.1', 52079)
2026-08-18 07:42:34,112 [INFO] - [('127.0.0.1', 52084) | bot_9] Overwrite existing dummy_9.bin
2026-08-18 07:42:34,113 [INFO] - [('127.0.0.1', 52084) | bot_9] Start UPLOAD dummy_9.bin (17310 bytes)
2026-08-18 07:42:34,117 [INFO] - [('127.0.0.1', 52084) | bot_9] UPLOAD dummy_9.bin completed. Session avg speed: 7345.05 KB/s
2026-08-18 07:42:34,135 [INFO] - Disconnected from ('127.0.0.1', 52084)
2026-08-18 07:42:34,145 [INFO] - [('127.0.0.1', 52077) | bot_2] Resume UPLOAD dummy_2.bin from 21148/41584
2026-08-18 07:42:34,148 [INFO] - [('127.0.0.1', 52077) | bot_2] UPLOAD dummy_2.bin completed. Session avg speed: 18700.93 KB/s
2026-08-18 07:42:34,163 [INFO] - Disconnected from ('127.0.0.1', 52077)
2026-08-18 07:42:34,165 [INFO] - [('127.0.0.1', 52083) | bot_8] Overwrite existing dummy_8.bin
2026-08-18 07:42:34,166 [INFO] - [('127.0.0.1', 52083) | bot_8] Start UPLOAD dummy_8.bin (27190 bytes)
2026-08-18 07:42:34,169 [INFO] - [('127.0.0.1', 52083) | bot_8] UPLOAD dummy_8.bin completed. Session avg speed: 16135.94 KB/s
2026-08-18 07:42:34,183 [INFO] - Disconnected from ('127.0.0.1', 52083)
2026-08-18 07:42:34,212 [INFO] - [('127.0.0.1', 52076) | bot_1] Overwrite existing dummy_1.bin
2026-08-18 07:42:34,214 [INFO] - [('127.0.0.1', 52076) | bot_1] Start UPLOAD dummy_1.bin (2036 bytes)
2026-08-18 07:42:34,217 [INFO] - [('127.0.0.1', 52076) | bot_1] UPLOAD dummy_1.bin completed. Session avg speed: 987.85 KB/s 
2026-08-18 07:42:34,229 [INFO] - [('127.0.0.1', 52080) | bot_5] Overwrite existing dummy_5.bin
2026-08-18 07:42:34,231 [INFO] - [('127.0.0.1', 52080) | bot_5] Start UPLOAD dummy_5.bin (48570 bytes)
2026-08-18 07:42:34,232 [INFO] - Disconnected from ('127.0.0.1', 52076)
2026-08-18 07:42:34,234 [INFO] - [('127.0.0.1', 52080) | bot_5] UPLOAD dummy_5.bin completed. Session avg speed: 17816.83 KB/s
2026-08-18 07:42:34,259 [INFO] - Disconnected from ('127.0.0.1', 52080)

client:
Starting stress test simulation with 10 concurrent clients on 127.0.0.1:9090...
[Client 3] Connected as bot_3
[Client 2] Connected as bot_2
[Client 4] Connected as bot_4
[Client 5] Connected as bot_5
[Client 8] Connected as bot_8
[Client 9] Connected as bot_9
[Client 10] Connected as bot_10
[Client 1] Connected as bot_1
[Client 7] Connected as bot_7
[Client 6] Connected as bot_6
[Client 7] Uploaded dummy_7.bin (18444 bytes)
[Client 7] Server verified checksum successfully.
[Client 7] Finished and disconnected safely.
[Client 6] Uploaded dummy_6.bin (40297 bytes)
[Client 6] Server verified checksum successfully.
[Client 6] Finished and disconnected safely.
[Client 3] Uploaded dummy_3.bin (14862 bytes)
[Client 3] Server verified checksum successfully.
[Client 3] Finished and disconnected safely.
[Client 10] Uploaded dummy_10.bin (38515 bytes)
[Client 10] Server verified checksum successfully.
[Client 10] Finished and disconnected safely.
[Client 4] Uploaded dummy_4.bin (43965 bytes)
[Client 4] Server verified checksum successfully.
[Client 4] Finished and disconnected safely.
[Client 9] Uploaded dummy_9.bin (17310 bytes)
[Client 9] Server verified checksum successfully.
[Client 9] Finished and disconnected safely.
[Client 2] Uploaded dummy_2.bin (41584 bytes)
[Client 2] Server verified checksum successfully.
[Client 2] Finished and disconnected safely.
[Client 8] Uploaded dummy_8.bin (27190 bytes)
[Client 8] Server verified checksum successfully.
[Client 8] Finished and disconnected safely.
[Client 1] Uploaded dummy_1.bin (2036 bytes)
[Client 1] Server verified checksum successfully.
[Client 1] Finished and disconnected safely.
[Client 5] Uploaded dummy_5.bin (48570 bytes)
[Client 5] Server verified checksum successfully.
[Client 5] Finished and disconnected safely.
Stress test completed in 0.52 seconds.
```

### **4.2. Bài kiểm tra giới hạn băng thông & tracking thời gian thực**
- **Kịch bản:** Upload và Download file `winlibs-x86_64-posix-seh-gcc-14.2.0-mingw-w64ucrt-12.0.0-r2` (Kích thước ~99.4MB).
- **Kết quả:**
  - Thanh tiến trình `tqdm` trên Terminal hiển thị liên tục phần trăm theo thời gian thực dựa trên từng khối byte (16KB) được truyền qua Socket.
  - Tốc độ hội tụ và duy trì ổn định ở mức ~502 KB/s (Gần tuyệt đối với cấu hình 500 KB/s do tính chất Burst của Token Bucket).

<p align="center">
  <img src="../anh_chup_log_server_upload.png" alt="Kết quả log từ server khi thực hiện xong lệnh UPLOAD" width="90%">
</p>

<p align="center">
  <img src="../anh_chup_log_client_upload.png" alt="Kết quả log từ client khi thực hiện xong lệnh UPLOAD" width="90%">
</p>

<p align="center">
  <img src="../anh_chup_log_server_download.png" alt="Kết quả log từ server khi thực hiện xong lệnh DOWNLOAD" width="90%">
</p>

<p align="center">
  <img src="../anh_chup_log_client_download.png" alt="Kết quả log từ client khi thực hiện xong lệnh DOWNLOAD" width="90%">
</p>

### **4.3. Bài kiểm tra resume & checksum**
- **Kịch bản:** Upload file 99.4MB, ngắt kết nối `Ctrl+C` tại thời điểm 9%. Sau đó chạy lại lệnh upload đúng file đó.
- **Kết quả:** 
  - Terminal ghi nhận rõ ràng: `Resuming upload from 9355264/104255184 bytes...`
  - Cuối quá trình tải, MD5 Hash giữa Client và Server khớp nhau hoàn toàn, Terminal báo `Upload successful! Checksum verified.`.

<p align="center">
  <img src="../anh_chup_log_server_resume.png" alt="Kết quả log từ server khi resume và truyền xong file" width="90%">
</p>

<p align="center">
  <img src="../anh_chup_log_client_resume_va_checksum.png" alt="Kết quả log từ client khi resume và checksum xong" width="90%">
</p>
