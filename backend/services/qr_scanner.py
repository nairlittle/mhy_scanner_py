"""二维码扫描服务 - OpenCV WeChatQRCode二维码检测"""

import os
from typing import Optional

import cv2
import numpy as np

# 模型文件目录
_MODEL_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "models")


class QRScanner:
    """二维码扫描器，基于OpenCV WeChatQRCode模型"""
    
    def __init__(self):
        self._detector = None
        self._fallback = None
        self._init_detector()
    
    def _init_detector(self):
        """初始化WeChatQRCode检测器"""
        detect_prototxt = os.path.join(_MODEL_DIR, "detect.prototxt")
        detect_caffemodel = os.path.join(_MODEL_DIR, "detect.caffemodel")
        sr_prototxt = os.path.join(_MODEL_DIR, "sr.prototxt")
        sr_caffemodel = os.path.join(_MODEL_DIR, "sr.caffemodel")
        
        missing = [f for f in [detect_prototxt, detect_caffemodel, sr_prototxt, sr_caffemodel] if not os.path.exists(f)]
        if missing:
            print(f"[WARN] 缺少QR模型文件，降级使用OpenCV内置QRCodeDetector")
            self._detector = None
            self._fallback = cv2.QRCodeDetector()
            return
        
        try:
            self._detector = cv2.wechat_qrcode_WeChatQRCode(
                detect_prototxt, detect_caffemodel,
                sr_prototxt, sr_caffemodel
            )
            print(f"[INFO] WeChatQRCode模型加载成功")
        except Exception as e:
            print(f"[WARN] 初始化WeChatQRCode失败: {e}，使用内置检测器")
            self._detector = None
            self._fallback = cv2.QRCodeDetector()
    
    def decode(self, frame: np.ndarray) -> Optional[str]:
        """解码单帧图像中的二维码
        
        Args:
            frame: BGR格式的numpy图像数组
        
        Returns:
            解码后的字符串，未检测到时返回None
        """
        if frame is None or frame.size == 0:
            return None
        
        try:
            # 确保是BGR/RGB格式
            if len(frame.shape) == 2:
                frame = cv2.cvtColor(frame, cv2.COLOR_GRAY2BGR)
            elif frame.shape[2] == 4:
                frame = cv2.cvtColor(frame, cv2.COLOR_RGBA2BGR)
            
            if self._detector is not None:
                results, _ = self._detector.detectAndDecode(frame)
                if results and results[0]:
                    return results[0]
            elif self._fallback is not None:
                data, _, _ = self._fallback.detectAndDecode(frame)
                if data:
                    return data
            
            return None
        except Exception as e:
            print(f"[ERROR] QR解码异常: {e}")
            return None
    
    def decode_multiple(self, frame: np.ndarray) -> list[str]:
        """解码多个二维码（用于多码场景）"""
        if frame is None or frame.size == 0:
            return []
        
        try:
            if len(frame.shape) == 2:
                frame = cv2.cvtColor(frame, cv2.COLOR_GRAY2BGR)
            elif frame.shape[2] == 4:
                frame = cv2.cvtColor(frame, cv2.COLOR_RGBA2BGR)
            
            if self._detector is not None:
                results, _ = self._detector.detectAndDecode(frame)
                return [r for r in results if r]
            
            return []
        except Exception:
            return []


_scanner: Optional[QRScanner] = None


def get_scanner() -> QRScanner:
    """获取全局QRScanner单例"""
    global _scanner
    if _scanner is None:
        _scanner = QRScanner()
    return _scanner


def decode_qr_from_bytes(data: bytes, width: int, height: int, channels: int = 3) -> Optional[str]:
    """从原始字节数据解码二维码（用于WebSocket传来的帧数据）
    
    Args:
        data: 原始像素数据
        width: 图像宽度
        height: 图像高度
        channels: 通道数 (3=RGB, 4=RGBA)
    """
    try:
        frame = np.frombuffer(data, dtype=np.uint8).reshape((height, width, channels))
        if channels == 4:
            frame = cv2.cvtColor(frame, cv2.COLOR_RGBA2BGR)
        else:
            frame = cv2.cvtColor(frame, cv2.COLOR_RGB2BGR)
        return get_scanner().decode(frame)
    except Exception as e:
        print(f"[ERROR] 帧解码失败: {e}")
        return None
