import asyncio
import base64
import io
import tkinter as tk
from tkinter import messagebox
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
import psutil
import mss
from PIL import Image
import os
import subprocess
import pyautogui
import threading

app = FastAPI()

# Cho phép Frontend kết nối chéo domain (nếu chạy khác port)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

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

def get_screenshot_base64() -> str:
    """Chụp màn hình, nén thành JPEG và chuyển sang Base64"""
    with mss.mss() as sct:
        monitor = sct.monitors[1] # Màn hình chính
        sct_img = sct.grab(monitor)
        
        # Chuyển đổi bytes raw sang ảnh JPEG để giảm băng thông
        img = Image.frombytes("RGB", sct_img.size, sct_img.bgra, "raw", "BGRX")
        buf = io.BytesIO()
        # Quality=40 để stream mượt hơn, giảm độ trễ WebSockets
        img.save(buf, format="JPEG", quality=40) 
        
        return base64.b64encode(buf.getvalue()).decode('utf-8')

async def send_system_data(websocket: WebSocket):
    """Luồng 1: Liên tục gửi thông số và màn hình cho Client"""
    try:
        while True:
            stats = get_system_stats()
            frame = await asyncio.to_thread(get_screenshot_base64)
            await websocket.send_json({"type": "data", "stats": stats, "frame": frame})
            await asyncio.sleep(1) # Stream 1 FPS
    except WebSocketDisconnect:
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

                # Dùng thread để click nhằm tránh block luồng WebSockets
                threading.Thread(target=pyautogui.click, args=(target_x, target_y)).start()
            elif action == "key_press":
                key = data.get("key")
                if key:
                    # Dùng thread để không block luồng WebSockets
                    threading.Thread(target=pyautogui.press, args=(key,)).start()
                    
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