"""WebSocket路由 - 实时扫码通信"""

import asyncio
import json
from typing import Optional

from fastapi import APIRouter, WebSocket, WebSocketDisconnect

from ..services.qr_scanner import decode_qr_from_bytes, get_scanner
from ..services.live_stream import stream_frames, LivePlatform

router = APIRouter()


@router.websocket("/ws/screen_scan")
async def screen_scan_ws(websocket: WebSocket):
    """屏幕扫码WebSocket - 接收前端传来的屏幕帧，返回识别到的二维码"""
    await websocket.accept()
    
    last_qr: Optional[str] = None
    frame_count = 0
    
    print("[SCAN_WS] 客户端已连接，等待帧数据...")
    
    try:
        while True:
            msg = await websocket.receive_bytes()
            frame_count += 1
            
            if len(msg) < 6:
                print(f"[SCAN_WS] 第{frame_count}帧 太短({len(msg)}字节) 跳过")
                continue
            
            # 解析宽度和高度
            width = int.from_bytes(msg[0:2], "big")
            height = int.from_bytes(msg[2:4], "big")
            frame_data = msg[4:]
            
            # 支持RGB(3)和RGBA(4)两种格式
            data_len = len(frame_data)
            pixel_count = width * height
            
            if data_len == pixel_count * 4:
                qr_text = decode_qr_from_bytes(frame_data, width, height, channels=4)
            elif data_len == pixel_count * 3:
                qr_text = decode_qr_from_bytes(frame_data, width, height, channels=3)
            else:
                if frame_count <= 3:
                    print(f"[SCAN_WS] 帧#{frame_count} 大小不匹配 w={width} h={height} expected={pixel_count*3}~{pixel_count*4} got={data_len}")
                continue
            
            if frame_count <= 1:
                print(f"[SCAN_WS] 首帧收到 {width}x{height} ch={data_len//pixel_count} 解码={'OK' if qr_text else '无QR'}")
            
            if qr_text and qr_text != last_qr:
                last_qr = qr_text
                print(f"[SCAN_WS] 第{frame_count}帧 检测到QR: {qr_text}")
                await websocket.send_json({
                    "type": "qr_detected",
                    "data": qr_text
                })
            
            # 每帧都发送心跳，避免超时
            # 不发送太多无用消息
            
    except WebSocketDisconnect:
        pass
    except Exception as e:
        try:
            await websocket.send_json({"type": "error", "data": str(e)})
        except:
            pass


@router.websocket("/ws/live_scan")
async def live_scan_ws(websocket: WebSocket):
    """直播扫码WebSocket - 接收前端发来的直播间信息，回传识别到的二维码"""
    await websocket.accept()
    
    scanner = get_scanner()
    current_task: Optional[asyncio.Task] = None
    last_qr: Optional[str] = None
    
    async def stream_processor(platform: str, room_id: str):
        nonlocal last_qr
        try:
            plat = LivePlatform(platform)
            
            async for frame in stream_frames(plat, room_id):
                if isinstance(frame, str):
                    if frame.startswith("STATUS:"):
                        parts = frame[7:].split(":", 1)
                        await websocket.send_json({
                            "type": "status",
                            "status": parts[0],
                            "message": parts[1] if len(parts) > 1 else ""
                        })
                    elif frame.startswith("ERROR:"):
                        await websocket.send_json({
                            "type": "error",
                            "data": frame[7:]
                        })
                    continue
                
                qr_text = scanner.decode(frame)
                if qr_text and qr_text != last_qr:
                    last_qr = qr_text
                    await websocket.send_json({
                        "type": "qr_detected",
                        "data": qr_text
                    })
        except Exception as e:
            print(f"[LIVE_WS] stream_processor异常: {e}")
            try:
                await websocket.send_json({
                    "type": "error",
                    "data": f"直播流处理异常: {str(e)}"
                })
            except:
                pass
    
    try:
        while True:
            msg = await websocket.receive_text()
            data = json.loads(msg)
            action = data.get("action")
            
            if action == "start":
                # 停止之前的任务
                if current_task:
                    current_task.cancel()
                    try:
                        await current_task
                    except asyncio.CancelledError:
                        pass
                
                last_qr = None
                current_task = asyncio.create_task(
                    stream_processor(data["platform"], data["room_id"])
                )
            
            elif action == "stop":
                if current_task:
                    current_task.cancel()
                    try:
                        await current_task
                    except asyncio.CancelledError:
                        pass
                    current_task = None
                await websocket.send_json({"type": "status", "status": "stopped", "message": "已停止"})
    
    except WebSocketDisconnect:
        pass
    finally:
        if current_task:
            current_task.cancel()
            try:
                await current_task
            except asyncio.CancelledError:
                pass
