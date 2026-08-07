# Hướng Dẫn Sử Dụng và Kiểm Thử Hệ Thống

Tài liệu này cung cấp các bước chi tiết để mọi người có thể chạy, sử dụng và kiểm thử các tính năng nâng cao của đồ án Mạng Máy Tính (Giai đoạn 2) sau khi tải mã nguồn về.

---

## 1. Chuẩn bị môi trường

Trước khi chạy hệ thống, ta cần cài đặt thư viện `tqdm` để hiển thị thanh tiến trình truyền file.
Mở Terminal tại thư mục gốc của dự án và chạy lệnh:
```bash
pip install -r requirements.txt
```

---

## 2. Cách khởi động Server

Server sử dụng kiến trúc Bất đồng bộ (Asyncio) và có cơ chế giới hạn tốc độ (Throttler). Để khởi động:
1. Mở một cửa sổ Terminal (hoặc Command Prompt).
2. Đứng tại thư mục gốc của dự án, chạy lệnh:
   ```bash
   python src/server.py
   ```
3. Server sẽ báo `Phase 2 Async Server started on ('127.0.0.1', 8080)`. Hãy giữ Terminal này luôn mở.

---

## 3. Cách sử dụng Client (Cơ bản)

1. Mở một cửa sổ Terminal mới.
2. Chạy ứng dụng Client:
   ```bash
   python src/client.py
   ```
3. **Đăng nhập:** Hệ thống sẽ yêu cầu nhập `username`. Ta nhập tên bất kỳ (vd: `alice` hoặc `bob`). *Lưu ý: Mỗi user sẽ có một không gian lưu trữ riêng biệt trên Server tại `storage/<username>`. Mô tả đồ án của thầy không yêu cầu mật khẩu để chặn trùng lặp; nếu nhiều Client đăng nhập cùng một username, họ sẽ dùng chung một không gian lưu trữ (file tải lên trùng tên sẽ ghi đè lên file cũ).*
4. **Các lệnh hỗ trợ:** Tại dấu nhắc `FTP>`, ta có thể dùng các lệnh:
   - `LIST`: Xem danh sách các file hiện có trong thư mục cá nhân trên Server.
   - `UPLOAD <đường_dẫn_file>`: Tải một file từ máy tính lên Server. 
     - *Ví dụ:* `UPLOAD C:\Users\HP\Downloads\tai_lieu.pdf`
   - `DOWNLOAD <tên_file>`: Tải một file từ Server về máy tính (file sẽ nằm trong thư mục `downloads/`).
     - *Ví dụ:* `DOWNLOAD tai_lieu.pdf`
   - `QUIT`: Thoát khỏi chương trình an toàn.

*Trong quá trình truyền file, thanh tiến trình % sẽ hiện ra kèm tốc độ thực tế (được giới hạn mặc định ở ~500 KB/s).*

---

## 4. Kiểm thử Cơ chế Truyền tiếp (Resume) và Checksum

1. Dùng Client chạy lệnh tải một file lớn (khuyên dùng file > 10MB để dễ thao tác):
   ```bash
   FTP> UPLOAD C:\path\to\file_rat_nang.zip
   ```
2. Đợi thanh tiến trình chạy được khoảng 5% - 10%, bấm tổ hợp phím `Ctrl + C` để tắt ngang Client. (Lúc này file trên Server đang bị tải dở dang).
3. Mở lại Terminal, chạy lại Client (`python src/client.py`), đăng nhập đúng username cũ.
4. Gõ lại y hệt lệnh UPLOAD lúc nãy:
   ```bash
   FTP> UPLOAD C:\path\to\file_rat_nang.zip
   ```
5. **Kết quả kỳ vọng:**
   - Client sẽ không tải lại từ 0% mà báo: `Resuming upload from <số_byte_đã_tải>...`
   - Thanh tiến trình sẽ nhảy vọt lên đúng mức % lúc nãy và tiếp tục tải.
   - Khi chạy xong 100%, hệ thống tự động băm MD5 và báo: `Upload successful! Checksum verified.`

*(Lưu ý: Tính năng Resume và Checksum hoạt động hoàn hảo cho cả chiều DOWNLOAD).*

---

## 5. Kịch bản Stress Test (Chạy 10 Client song song)

Mục đích của kịch bản này là kiểm tra độ trâu bò của Server khi bị spam dữ liệu dồn dập từ nhiều nguồn cùng lúc mà không bị Deadlock hay Crash.

1. Hãy đảm bảo Server đang chạy ở một Terminal riêng.
2. Mở một Terminal mới, chạy script kiểm thử tự động:
   ```bash
   python tests/simulate_multi_client.py
   ```
3.
   - Script sẽ tự động sinh ra 10 file rác ngẫu nhiên.
   - Cùng một lúc, nó tạo ra 10 Client kết nối tới Server, đăng nhập từ `bot_1` đến `bot_10`.
   - Cả 10 bot đồng loạt bắn dữ liệu lên Server.
   - Server xử lý mượt mà, băm MD5 cho từng bot và trả về kết quả.
   - Bạn sẽ thấy Terminal hiện ra hàng loạt thông báo `Server verified checksum successfully.` và `Finished and disconnected safely.`
   - Có thể ngó qua Terminal của Server để chiêm ngưỡng log tốc độ của 10 luồng xử lý song song.


