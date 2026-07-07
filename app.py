import sys
import uvicorn
from backend.main import app as fastapi_app
import tkinter as tk
from tkinter import messagebox
import socket
import threading
import random
import subprocess
import os
import time
import webbrowser

if sys.stdout is None:
    sys.stdout = open(os.devnull, "w")
if sys.stderr is None:
    sys.stderr = open(os.devnull, "w")
    
BROADCAST_PORT = 9999

def get_local_ip():
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(('8.8.8.8', 80))
        ip = s.getsockname()[0]
        s.close()
        return ip
    except:
        return '127.0.0.1'

def udp_broadcaster(pin, ip):
    """Liên tục phát sóng mã PIN và IP lên mạng LAN"""
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    s.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
    while True:
        msg = f"{pin}:{ip}"
        s.sendto(msg.encode(), ('<broadcast>', BROADCAST_PORT))
        time.sleep(1)

def get_resource_path(relative_path):
    # Hàm này giống hệt hàm trong main.py, hãy copy nó vào app.py
    try:
        base_path = sys._MEIPASS
    except Exception:
        base_path = os.path.abspath(".")
    return os.path.join(base_path, relative_path)

def run_server():
    ip = get_local_ip()
    pin = str(random.randint(100000, 999999))
    
    # Chạy trực tiếp FastAPI trong một luồng ngầm
    threading.Thread(target=lambda: uvicorn.run(fastapi_app, host="0.0.0.0", port=8000), daemon=True).start()
    
    # Bật luồng phát sóng UDP
    threading.Thread(target=udp_broadcaster, args=(pin, ip), daemon=True).start()
    
    # Đổi giao diện
    frame_main.pack_forget()
    frame_server.pack(pady=30)
    lbl_pin.config(text=pin)

def run_client():
    def connect_via_pin():
        pin_input = entry_pin.get().strip()
        if len(pin_input) != 6:
            messagebox.showerror("Lỗi", "Mã PIN phải có đúng 6 số!")
            return
            
        lbl_status.config(text="Đang quét mạng LAN tìm Server...", fg="orange")
        root.update()
        
        # Dùng UDP để lắng nghe xem Server nào đang hét đúng mã PIN này
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.bind(('', BROADCAST_PORT))
        s.settimeout(4.0) # Chờ tối đa 4 giây
        
        try:
            while True:
                data, _ = s.recvfrom(1024)
                msg = data.decode()
                if ":" in msg:
                    recv_pin, recv_ip = msg.split(":")
                    if recv_pin == pin_input:
                        lbl_status.config(text="Đã tìm thấy! Đang kết nối...", fg="green")
                        # Mở trình duyệt và truyền IP vào URL
                        lbl_status.config(text="Đã tìm thấy! Đang kết nối...", fg="green")
                        webbrowser.open(f"http://{recv_ip}:8000/?ip={recv_ip}")
                        root.destroy() # Tắt app launcher
                        break
        except socket.timeout:
            messagebox.showerror("Thất bại", f"Không tìm thấy Server nào có mã {pin_input} trong mạng LAN. Hãy kiểm tra lại Tường lửa hoặc mạng Wifi.")
        finally:
            s.close()

    # Đổi giao diện
    frame_main.pack_forget()
    frame_client.pack(pady=20)
    btn_do_connect.config(command=connect_via_pin)

# --- THIẾT KẾ GIAO DIỆN APP ---
root = tk.Tk()
root.title("RMM - Điều Khiển Từ Xa")
root.geometry("350x220")
root.configure(bg="#f0f0f0")

# 1. Màn hình chính (Chọn chế độ)
frame_main = tk.Frame(root, bg="#f0f0f0")
tk.Label(frame_main, text="BẠN MUỐN LÀM GÌ?", font=("Arial", 12, "bold"), bg="#f0f0f0").pack(pady=15)
tk.Button(frame_main, text="💻 CHẠY LÀM SERVER\n(Cho phép người khác điều khiển máy này)", command=run_server, bg="#d9534f", fg="white", font=("Arial", 10, "bold"), width=35).pack(pady=5)
tk.Button(frame_main, text="🎮 CHẠY LÀM CLIENT\n(Đi điều khiển máy tính khác)", command=run_client, bg="#0275d8", fg="white", font=("Arial", 10, "bold"), width=35).pack(pady=5)
frame_main.pack(fill="both", expand=True)

# 2. Màn hình Server (Đang đợi)
frame_server = tk.Frame(root, bg="#f0f0f0")
tk.Label(frame_server, text="Hệ thống đã sẵn sàng!", font=("Arial", 12), bg="#f0f0f0").pack()
tk.Label(frame_server, text="MÃ KẾT NỐI (PIN) CỦA BẠN:", font=("Arial", 10), bg="#f0f0f0", fg="gray").pack(pady=10)
lbl_pin = tk.Label(frame_server, text="------", font=("Courier", 32, "bold"), fg="red", bg="#f0f0f0")
lbl_pin.pack()

# 3. Màn hình Client (Nhập PIN)
frame_client = tk.Frame(root, bg="#f0f0f0")
tk.Label(frame_client, text="NHẬP MÃ 6 SỐ TỪ SERVER:", font=("Arial", 12, "bold"), bg="#f0f0f0").pack(pady=10)
entry_pin = tk.Entry(frame_client, font=("Courier", 24, "bold"), width=8, justify="center")
entry_pin.pack(pady=5)
btn_do_connect = tk.Button(frame_client, text="KẾT NỐI NGAY", bg="#5cb85c", fg="white", font=("Arial", 11, "bold"), width=20)
btn_do_connect.pack(pady=10)
lbl_status = tk.Label(frame_client, text="", bg="#f0f0f0", font=("Arial", 9))
lbl_status.pack()

root.mainloop()