import asyncio
import base64
import io
import tkinter as tk
from tkinter import messagebox
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.responses import FileResponse
from fastapi.middleware.cors import CORSMiddleware
import psutil
import mss
from PIL import Image
import os
import subprocess
import pyautogui
import ctypes

app = FastAPI()

# Cho phép Frontend kết nối chéo domain (nếu chạy khác port)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
# ---> THÊM KHỐI LỆNH NÀY VÀO <---
@app.get("/")
async def serve_frontend():
    """Khi truy cập vào IP gốc, tự động trả về giao diện Web"""
    return FileResponse("frontend/index.html")
# --------------------------------

def ask_permission(client_ip: str) -> bool:
    """Hiển thị popup xin quyền trên máy Server (Host)"""
    root = tk.Tk()
    root.withdraw() # Ẩn cửa sổ chính
    root.attributes("-topmost", True) # Luôn nổi trên cùng
    result = messagebox.askyesno(
        "Yêu cầu giám sát hệ thống", 
        f"Thiết bị Client ({client_ip}) đang yêu cầu giám sát và xem màn hình.\nBạn có đồng ý không?"
    )
    root.destroy()
    return result

def get_system_stats():
    """Lấy thông số CPU, RAM, Disk và danh sách Process"""
    # Lấy thông số tổng quan
    cpu = psutil.cpu_percent(interval=None)
    ram = psutil.virtual_memory().percent
    disk = psutil.disk_usage('/').percent
    
    # Lấy Top 10 Process ngốn RAM nhất
    processes = []
    for proc in psutil.process_iter(['pid', 'name', 'memory_info']):
        try:
            mem_mb = proc.info['memory_info'].rss / (1024 * 1024)
            processes.append({
                "pid": proc.info['pid'],
                "name": proc.info['name'],
                "memory": round(mem_mb, 2)
            })
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            continue
            
    processes = sorted(processes, key=lambda x: x['memory'], reverse=True)[:10]
    
    return {"cpu": cpu, "ram": ram, "disk": disk, "processes": processes}

def get_screenshot_base64():
    with mss.mss() as sct:
        # 1. Chụp màn hình chính
        monitor = sct.monitors[1]
        sct_img = sct.grab(monitor)
        
        # 2. Chuyển dữ liệu thô sang đối tượng ảnh PIL
        img = Image.frombytes("RGB", sct_img.size, sct_img.bgra, "raw", "BGRX")
        
        # 3. ÉP XUNG: Thu nhỏ kích thước ảnh đi 80% để truyền cho lẹ
        new_width = int(img.width * 0.8)
        new_height = int(img.height * 0.8)
        img = img.resize((new_width, new_height), Image.Resampling.BILINEAR)
        
        # 4. Lưu ảnh dưới dạng JPEG với chất lượng nén còn 85%
        buffer = io.BytesIO()
        img.save(buffer, format="JPEG", quality=85)
        
        # 5. Mã hóa sang Base64 và gửi đi
        return base64.b64encode(buffer.getvalue()).decode("utf-8")

async def send_system_data(websocket: WebSocket):
    """Luồng 1: Liên tục gửi thông số và màn hình cho Client"""
    try:
        while True:
            stats = get_system_stats()
            frame = await asyncio.to_thread(get_screenshot_base64)
            await websocket.send_json({"type": "data", "stats": stats, "frame": frame})
            
            # GIẢM ĐỘ TRỄ XUỐNG: 
            # 0.05 giây/hình tương đương khoảng 20 FPS (Rất mượt)
            await asyncio.sleep(0.05) 
            
    except Exception:
        pass # Client ngắt kết nối

async def receive_commands(websocket: WebSocket):
    """Luồng 2: Lắng nghe và thực thi lệnh từ Client gửi lên"""
    try:
        while True:
            # Nhận JSON từ giao diện Web
            data = await websocket.receive_json()
            action = data.get("action")
            
            # Xử lý lệnh Tắt tiến trình
            if action == "kill_process":
                pid = data.get("pid")
                try:
                    # Dùng psutil tìm và diệt process theo PID
                    process = psutil.Process(pid)
                    process.kill()
                    await websocket.send_json({"type": "alert", "msg": f"Thành công: Đã đóng tiến trình PID {pid}!"})
                except psutil.NoSuchProcess:
                    await websocket.send_json({"type": "alert", "msg": f"Lỗi: Không tìm thấy PID {pid} (Có thể đã tự đóng)."})
                except psutil.AccessDenied:
                    await websocket.send_json({"type": "alert", "msg": f"Lỗi: Không đủ quyền Admin để đóng PID {pid}."})
            elif action == "terminal":
                cmd = data.get("cmd")
                try:
                    # shell=True cho phép chạy lệnh cmd thuần, capture_output chụp lại kết quả
                    # errors='replace' để tránh lỗi font chữ tiếng Việt của Windows
                    result = subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=10, errors='replace')

                    # Ưu tiên lấy kết quả (stdout), nếu lệnh lỗi thì lấy báo lỗi (stderr)
                    output = result.stdout if result.stdout else result.stderr

                    if not output.strip():
                        output = f"Đã chạy lệnh: {cmd} (Không có kết quả văn bản trả về)"

                    await websocket.send_json({"type": "terminal_output", "data": output})

                except subprocess.TimeoutExpired:
                    await websocket.send_json({"type": "terminal_output", "data": f"Lỗi: Lệnh '{cmd}' chạy quá 10 giây (Bị ép dừng)!"})
                except Exception as e:
                    await websocket.send_json({"type": "terminal_output", "data": f"Lỗi thực thi: {str(e)}"})
            elif action == "mouse_click":
                # Nhận tọa độ X, Y dạng phần trăm (từ 0.0 đến 1.0) từ Web
                percent_x = data.get("x", 0)
                percent_y = data.get("y", 0)

                # Lấy kích thước thực tế của màn hình máy Host
                screen_w, screen_h = pyautogui.size()

                # Quy đổi phần trăm ra tọa độ pixel thực tế
                target_x = int(screen_w * percent_x)
                target_y = int(screen_h * percent_y)
                await asyncio.to_thread(pyautogui.click, target_x, target_y)
            elif action == "key_press":
                key = data.get("key")
                if key:
                    await asyncio.to_thread(pyautogui.press, key)
            # Xử lý lệnh Nguồn (Power Control)
            elif action == "power":
                cmd = data.get("cmd")
                if cmd == "shutdown":
                    # Lệnh tắt máy sau 5 giây (để OS kịp đóng các ứng dụng)
                    os.system("shutdown /s /t 5 /c \"Hệ thống sẽ tắt theo lệnh từ Remote Client\"")
                    await websocket.send_json({"type": "alert", "msg": "Đã gửi lệnh Tắt máy (Shutdown) xuống Server!"})
                elif cmd == "sleep":
                    # Lệnh đưa Windows vào chế độ Sleep
                    os.system("rundll32.exe powrprof.dll,SetSuspendState 0,1,0")
                    await websocket.send_json({"type": "alert", "msg": "Đã gửi lệnh Ngủ (Sleep) xuống Server!"})
            elif action == "take_screenshot":
                # 1. Lấy IP của máy Client đang ra lệnh
                client_ip = websocket.client.host
                
                # 2. Chụp ảnh màn hình chất lượng cao (PNG nguyên bản)
                with mss.mss() as sct:
                    monitor = sct.monitors[1]
                    sct_img = sct.grab(monitor)
                    img = Image.frombytes("RGB", sct_img.size, sct_img.bgra, "raw", "BGRX")
                    buffer = io.BytesIO()
                    img.save(buffer, format="PNG") 
                    b64_img = base64.b64encode(buffer.getvalue()).decode("utf-8")
                
                # 3. Gửi bức ảnh ngược về cho Client
                await websocket.send_json({"type": "screenshot_result", "data": b64_img})
                
                # 4. Hiển thị thông báo trên máy Server (Chạy bằng Thread để không làm treo hệ thống)
                def show_popup(ip):
                    # 0x40 | 0x0 là cờ để hiện icon Information (Chữ i) và nút OK
                    ctypes.windll.user32.MessageBoxW(0, f"Màn hình của bạn vừa được chụp lại bởi Client có IP: {ip}", "Thông Báo Quản Trị", 0x40 | 0x0)
                
                asyncio.create_task(asyncio.to_thread(show_popup, client_ip))

    except WebSocketDisconnect:
        pass

@app.websocket("/ws/monitor")
async def websocket_monitor(websocket: WebSocket):
    await websocket.accept()
    client_ip = websocket.client.host
    
    # 1. Cơ chế xin quyền (giữ nguyên)
    is_approved = await asyncio.to_thread(ask_permission, client_ip)
    
    if not is_approved:
        await websocket.send_json({"type": "error", "message": "Host đã từ chối yêu cầu giám sát!"})
        await websocket.close(code=1008)
        return
        
    await websocket.send_json({"type": "success", "message": "Kết nối thành công. Đang truyền dữ liệu..."})
    
    # 2. Khởi chạy 2 luồng (Gửi và Nhận) song song bằng asyncio.gather
    task_send = asyncio.create_task(send_system_data(websocket))
    task_recv = asyncio.create_task(receive_commands(websocket))
    
    await asyncio.gather(task_send, task_recv)

if __name__ == "__main__":
    import uvicorn
    # Khởi chạy server tại http://localhost:8000
    uvicorn.run(app, host="0.0.0.0", port=8000)