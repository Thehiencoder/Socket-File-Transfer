socket-file-transfer/
│
├── common/                        # Dùng chung GĐ1 & GĐ2
│   ├── framing.py                 # send_all() + recv_exact(sock, n), đọc/ghi socket mức byte thô,
│   │                               # dùng chung cho cả 2 giao thức để tránh lỗi recv() trả về thiếu byte
│   ├── logger.py                  # Dùng module logging chuẩn (thread-safe) 
│   ├── checksum.py                # Hash theo kiểu streaming (update() từng chunk, không đọc cả file)
│   └── file_manager.py            # Sanitize filename (chặn path traversal), seek/write theo offset,
│                                   # per-file lock, quản lý thư mục theo user
│
├── src (release phase 1)                      # Giai đoạn 1 — đơn luồng, length-prefix
│   ├── protocol.py             # Đóng khung: [4-byte length][command text] cho LIST/UPLOAD/DOWNLOAD,
│   │                               # và [8-byte length][file chunk x N] cho phần dữ liệu file
│   ├── server.py                  # Vòng lặp accept → handle tuần tự, try/except quanh mỗi phiên
│   │                               # để client rớt mạng không làm chết server
│   └── client.py                  # CLI: LIST / UPLOAD <filename> / DOWNLOAD <filename>
│
├── src (release phase 2)                        # Giai đoạn 2 — đa client, giao thức nhị phân tùy chỉnh
│   ├── protocol.py         # Struct Length–Opcode–UserID–Payload, bảng opcode 0x01–0xFF,
│   │                               # dùng struct.pack/unpack với network byte order (">")
│   ├── throttler.py                # Token bucket — 1 instance riêng cho mỗi client (không share global)
│   ├── server.py            # asyncio event-loop; I/O file qua run_in_executor/aiofiles để không
│   │                               # block event loop; semaphore giới hạn max client; cleanup
│   │                               # resource khi client disconnect
│   └── client.py            # Async client: progress bar, detect mất kết nối → reconnect →
│                                   # gửi lại FILE_UPLOAD mở đầu → nhận next_offset từ ACK → resume
│
├── storage/
│   ├── default/                   # Lưu file cho Giai đoạn 1
│   └── <username>/                # Namespace riêng theo user — Giai đoạn 2
│
├── tests/                         # Script kiểm chứng
│   ├── test_framing.py            # Unit test recv_exact với gói tin bị chia nhỏ
│   ├── test_checksum.py           # Test checksum khớp/không khớp
│   ├── corrupt_file.py            # Giả lập làm hỏng file để test cảnh báo checksum
│   ├── simulate_multi_client.py   # Giả lập tối thiểu 10 client đồng thời
│   └── simulate_disconnect.py     # Ngắt kết nối giữa chừng khi upload/download để test resume
│
├── docs/                          
│   ├── protocol_spec.md           # Mini-RFC: bảng opcode, định dạng payload từng loại, ví dụ hex dump
│   └── report.md                  # Bản nháp báo cáo (kiến trúc, đo tốc độ, giải thích lựa chọn kỹ thuật)
│
├── config.py                      # PORT, CHUNK_SIZE, MAX_CLIENTS, SPEED_LIMIT_KBPS, DUPLICATE_FILE_POLICY
├── requirements.txt               # Nếu dùng thư viện ngoài stdlib (vd: tqdm cho progress bar)
└── README.md                      # Hướng dẫn chạy server/client, cách demo resume