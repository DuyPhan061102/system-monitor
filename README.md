# 🖥️ Remote System Monitor & Manager

Dự án Hệ thống Giám sát và Điều khiển máy tính từ xa (Remote Monitoring and Management) hoạt động trên nền tảng Web. Hệ thống ứng dụng mô hình Client-Server, giao tiếp theo thời gian thực (Real-time) thông qua giao thức WebSockets.

---

## ✨ Các tính năng chính

- **📊 Giám sát tài nguyên:** Hiển thị phần trăm sử dụng CPU, RAM, Disk theo thời gian thực.
- **📺 Live Screen:** Truyền phát hình ảnh màn hình của Server với độ trễ thấp (khoảng 20 FPS).
- **🖱️ Điều khiển từ xa:** Hỗ trợ click chuột và gõ phím trực tiếp trên khung Live Screen.
- **💻 Remote Terminal:** Cho phép gửi và thực thi các lệnh CMD ngầm trên Server và nhận kết quả trả về.
- **⚙️ Quản lý tiến trình (Task Manager):** Hiển thị Top 10 ứng dụng ngốn RAM nhất và cho phép "Kill" tiến trình từ xa.
- **🔌 Quản lý nguồn & Chụp ảnh:** Chụp ảnh màn hình (tải trực tiếp về Client), Sleep và Shutdown máy Server.
- **🔒 Bảo mật (Host Consent):** Mọi yêu cầu kết nối từ Client đều phải được Host (Server) xác nhận thông qua Popup trước khi truyền dữ liệu.

---

## 📂 Cấu trúc dự án

Dự án được chia thành 2 thành phần độc lập (Frontend và Backend):

```text
📁 system-monitor/
├── 📁 backend/
│   └── 📄 main.py             # Mã nguồn Server (FastAPI, Uvicorn, WebSockets)
├── 📁 frontend/
│   └── 📄 index.html          # Giao diện điều khiển (HTML, TailwindCSS, JS thuần)
├── 📄 requirements.txt    # Danh sách các thư viện Python
└── 📄 README.md           # Tài liệu hướng dẫn
