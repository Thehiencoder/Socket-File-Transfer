# Đặc tả Giao thức Nhị phân - Giai đoạn 2 (Mini-RFC)

## 1. Cấu trúc Gói tin Chung (Header)
Mọi gói tin truyền đi trong Giai đoạn 2 đều tuân theo một Header cố định dài **8 byte**, cấu trúc như sau:

| Field | Size (Bytes) | Type | Mổ tả |
| --- | --- | --- | --- |
| `Length` | 4 | Unsigned Int (`!I`) | Kích thước của phần Payload (không tính Header). Có thể lên tới 4GB. |
| `Opcode` | 2 | Unsigned Short (`!H`) | Mã lệnh định danh loại hành động. |
| `UserID` | 2 | Unsigned Short (`!H`) | Mã định danh client/user. (0 = Chưa đăng nhập). |

*Lưu ý: Tất cả các số nguyên đều được đóng gói theo **Network Byte Order (Big-Endian)** sử dụng dấu `!` trong thư viện `struct`.*

---

## 2. Bảng Opcode

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

---

## 3. Cấu trúc Payload theo từng Opcode

### 3.1 `LOGIN` (0x01)
- **Payload**: Chuỗi UTF-8 tên username (ví dụ: `Alice`).

### 3.2 `LIST_REQ` (0x02)
- **Payload**: Trống (0 bytes).

### 3.3 `LIST_RESP` (0x03)
- **Payload**: Chuỗi UTF-8 danh sách file, cách nhau dấu phẩy. Ví dụ: `file1.txt,file2.zip`.

### 3.4 `UPLOAD_REQ` (0x04)
- Dùng cho cả gửi mới và Resume (truyền tiếp).
- **Payload Format**: `[Kích thước file: 8 byte (!Q)] [Tên file: chuỗi UTF-8 còn lại]`

### 3.5 `ACK` (0x09) trả lời cho `UPLOAD_REQ`
- Server kiểm tra file trên đĩa, nếu file đã tồn tại và chưa đủ dung lượng, server trả về offset hiện tại để client resume.
- **Payload Format**: `[next_offset: 8 byte (!Q)]`
- Nếu file chưa tồn tại (tải mới), `next_offset` = 0.

### 3.6 `DOWNLOAD_REQ` (0x05)
- **Payload Format**: `[offset hiện có ở client: 8 byte (!Q)] [Tên file: chuỗi UTF-8 còn lại]`
- Client truyền `offset` lên để báo cho Server biết nó đang có bao nhiêu byte, Server sẽ chỉ gửi từ `offset` đó trở đi (Resume Download).

### 3.7 `FILE_CHUNK` (0x06)
- **Payload**: Dữ liệu thô của file (bytes). 

### 3.8 `ERROR` (0x0A)
- **Payload**: Chuỗi UTF-8 báo lỗi. (VD: `INVALID_FILE`, `MAX_CLIENTS_REACHED`).

---

## 4. Ví dụ luồng Truyền tiếp (Resume)
1. Client gửi `UPLOAD_REQ` (Payload: `8 byte size` + `"video.mp4"`).
2. Server check `storage/user/video.mp4`, thấy có sẵn 10MB (10485760 bytes).
3. Server gửi lại `ACK` (Payload: `10485760` đóng gói 8 byte).
4. Client nhận được `ACK`, đọc file từ byte thứ 10485760.
5. Client liên tục gửi `FILE_CHUNK` đến khi hết file.

---

## 5. Ví dụ Hex Dump thực tế (Gói tin LOGIN)

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
