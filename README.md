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

🛠️ Yêu cầu hệ thống và Cài đặt
Đảm bảo máy tính đóng vai trò là Server đã cài đặt Python 3.8+.

Mở Terminal (CMD/PowerShell) tại thư mục gốc của dự án (system-monitor) và cài đặt các thư viện cần thiết bằng lệnh sau:

Bash
pip install fastapi uvicorn websockets psutil mss Pillow pyautogui
🚀 Hướng dẫn sử dụng
Kịch bản 1: Chạy thử nghiệm trên 1 máy (Localhost)
Dùng để test giao diện và các tính năng cơ bản.

Khởi động Server: Mở Terminal tại thư mục gốc và chạy lệnh:

Bash
python backend/main.py
(Server sẽ khởi chạy và lắng nghe tại http://0.0.0.0:8000)

Mở giao diện Client: Truy cập vào thư mục frontend, click đúp vào file index.html để mở bằng trình duyệt Web.

Kết nối: Tại ô nhập IP, giữ nguyên chữ localhost và bấm Kết nối Server.

Cấp quyền: Một bảng thông báo (Popup) sẽ hiện lên trên màn hình, bấm Yes để đồng ý cấp quyền.

Kịch bản 2: Chạy thực tế trên 2 máy riêng biệt (LAN / VPN)
Máy A đóng vai trò là Server (bị điều khiển). Máy B đóng vai trò là Client (người điều khiển).

Bước 1: Trên Máy A (Server)

Chạy lệnh python backend/main.py để bật Server.

Mở cửa sổ CMD mới, gõ lệnh ipconfig để lấy địa chỉ IP:

Nếu 2 máy dùng chung mạng Wi-Fi/LAN: Lấy IP ở dòng IPv4 Address của card Wi-Fi/Ethernet (Thường có dạng 192.168.x.x).

Nếu 2 máy ở xa nhau (dùng mạng ảo Radmin VPN / HotspotShield): Lấy IP ở card mạng ảo tương ứng (Ví dụ Radmin VPN thường có dạng 26.x.x.x).

(Quan trọng) Tắt tạm thời Windows Defender Firewall ở mục Public Network (hoặc tạo Rule cho phép cổng 8000 đi qua tường lửa).

Bước 2: Trên Máy B (Client)

Mở file index.html bằng trình duyệt Web. Không cần cài đặt Python hay thư viện.

Tại ô nhập IP trên góc phải, xóa chữ localhost và nhập địa chỉ IPv4 của Máy A vừa lấy ở Bước 1.

Bấm Kết nối Server.

Bước 3: Cấp quyền kết nối

Máy A sẽ xuất hiện một Popup cảnh báo an ninh xin quyền giám sát.

Chủ nhân Máy A bấm Yes để xác nhận. Ngay lập tức, hình ảnh và dữ liệu hệ thống của Máy A sẽ stream trực tiếp về trình duyệt của Máy B.
