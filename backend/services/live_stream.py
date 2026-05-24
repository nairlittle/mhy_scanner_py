"""直播流服务 - B站/抖音直播流URL获取与帧提取"""

import asyncio
import json
import subprocess
import re
from typing import Optional, AsyncIterator
from dataclasses import dataclass
from enum import Enum

import httpx
import numpy as np


class LivePlatform(Enum):
    BILIBILI = "bilibili"
    DOUYIN = "douyin"


class LiveStatus(Enum):
    NORMAL = "normal"
    NOT_LIVE = "not_live"
    ABSENT = "absent"
    ERROR = "error"


@dataclass
class LiveStreamInfo:
    status: LiveStatus
    url: str = ""
    message: str = ""


# B站直播间API
async def get_bilibili_stream_url(room_id: str) -> LiveStreamInfo:
    """获取B站直播流地址"""
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36",
        "Referer": "https://live.bilibili.com/",
        "Accept": "application/json",
    }
    
    async with httpx.AsyncClient(timeout=15) as client:
        # 获取房间信息
        try:
            resp = await client.get(
                "https://api.live.bilibili.com/room/v1/Room/room_init",
                params={"id": room_id},
                headers=headers
            )
        except httpx.HTTPError as e:
            print(f"[LIVE] B站 room_init HTTP错误: {e}")
            return LiveStreamInfo(LiveStatus.ERROR, message=f"网络请求失败: {e}")
        
        print(f"[LIVE] B站 room_init 返回: HTTP {resp.status_code}")
        
        try:
            data = resp.json()
        except Exception:
            print(f"[LIVE] B站 room_init 非JSON响应: {resp.text[:300]}")
            return LiveStreamInfo(LiveStatus.ERROR, message="B站API返回异常，可能被风控")
        
        print(f"[LIVE] B站 room_init code={data.get('code')} msg={data.get('message', '')}")
        
        if data.get("code") == 60004:
            return LiveStreamInfo(LiveStatus.ABSENT, message="直播间不存在")
        if data.get("code") != 0:
            return LiveStreamInfo(LiveStatus.ERROR, message=f"B站API错误(code={data.get('code')}): {data.get('message', '')}")
        
        real_room_id = data["data"]["room_id"]
        
        # 获取播放地址
        resp2 = await client.get(
            "https://api.live.bilibili.com/xlive/web-room/v2/index/getRoomPlayInfo",
            params={
                "room_id": real_room_id,
                "protocol": "0,1",
                "format": "0,2",
                "codec": "0",
                "qn": "10000",
                "only_audio": "0",
                "only_video": "0",
            },
            headers=headers
        )
        data2 = resp2.json()
        
        try:
            playurl = data2["data"]["playurl_info"]["playurl"]
            stream = playurl["stream"][0]
            fmt = stream["format"][0]
            codec = fmt["codec"][0]
            base_url = codec["base_url"]
            extra = codec["url_info"][0]["extra"]
            host = codec["url_info"][0]["host"]
            full_url = host + base_url + extra
            return LiveStreamInfo(LiveStatus.NORMAL, url=full_url)
        except (KeyError, IndexError):
            return LiveStreamInfo(LiveStatus.ERROR, message="解析流地址失败")


async def get_douyin_stream_url(room_id: str) -> LiveStreamInfo:
    """获取抖音直播流地址 - 对齐原版 LiveDouyin::GetLiveStreamInfo"""
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/92.0.4515.159 Safari/537.36",
        "referer": "https://live.douyin.com/",
        "cookie": "enter_pc_once=1; UIFID_TEMP=29a1f63ec682dc0a0df227dd163e2b46e3a6390e403335fa4c2c6d1dc0ec5ffa7a288170e8828ecb8b2f0f16b3219daa18ad5d7faf7fb5fbb64df454c3b471cc1db9c0b5eb2cbc8e0cb1e690f5c1fbd6; stream_recommend_feed_params=%22%7B%5C%22cookie_enabled%5C%22%3Atrue%2C%5C%22screen_width%5C%22%3A2560%2C%5C%22screen_height%5C%22%3A1440%2C%5C%22browser_online%5C%22%3Atrue%2C%5C%22cpu_core_num%5C%22%3A16%2C%5C%22device_memory%5C%22%3A8%2C%5C%22downlink%5C%22%3A10%2C%5C%22effective_type%5C%22%3A%5C%224g%5C%22%2C%5C%22round_trip_time%5C%22%3A50%7D%22; hevc_supported=true; odin_tt=363047b47492a2e153d67e7022684ffd83726a0c57322991e6650da1dbe2fc0adb471e8be38efa85bf0ab9788a8e237d481c8fc488ef859f4476fc6ffd50dd31a258add2954b3fcf03cd546357df6a53; strategyABtestKey=%221772897157.15%22; passport_csrf_token=d71952d93315e4df5cc8373e4cdc2447; passport_csrf_token_default=d71952d93315e4df5cc8373e4cdc2447; home_can_add_dy_2_desktop=%221%22; biz_trace_id=fab9d888; ttwid=1%7CP0feYUzzIsbXr2aaLLBWHYtwVD4-6CV2voO9bAUQ7PU%7C1772897161%7Cd72bed8f6f576a1dfb7b8d1032c76706ce93b3ba3ac5b21e79501db1c2f17c9f; __security_mc_1_s_sdk_crypt_sdk=0ef27763-40a0-b3c3; bd_ticket_guard_client_data=eyJiZC10aWNrZXQtZ3VhcmQtdmVyc2lvbiI6MiwiYmQtdGlja2V0LWd1YXJkLWl0ZXJhdGlvbi12ZXJzaW9uIjoxLCJiZC10aWNrZXQtZ3VhcmQtcmVlLXB1YmxpYy1rZXkiOiJCSjhja053TW16SWxIVWQzazF4d2F6bXdQdm1JZjUrcElEVWR2MmpTN3czVWRKRWZ6djBIN1g5Z3dINUNnRkpSSGIzOEFvWTZYSEZsOEdWcGd1dmN4OGc9IiwiYmQtdGlja2V0LWd1YXJkLXdlYi12ZXJzaW9uIjoyfQ%3D%3D; bd_ticket_guard_client_web_domain=2; bd_ticket_guard_client_data_v2=eyJyZWVfcHVibGljX2tleSI6IkJKOGNrTndNbXpJbEhVZDNrMXh3YXptd1B2bUlmNStwSURVZHYyalM3dzNVZEpFZnp2MEg3WDlnd0g1Q2dGSlJIYjM4QW9ZNlhIRmw4R1ZwZ3V2Y3g4Zz0iLCJyZXFfY29udGVudCI6InNlY190cyIsInJlcV9zaWduIjoiNkxSc0hxbFZ4bUhHSFVzMCtsQ0dLaGNlU242bVZxZzRRRFJmdjJ1RzZCaz0iLCJzZWNfdHMiOiIjaUZua3E0M0pNV25FWGlQNW15b3grVTlWdUNrL3B4ZnQveVlsL3o5eWdpWnRSOUZjbEZSSmFGOXk1T1lWIn0%3D; sdk_source_info=7e276470716a68645a606960273f276364697660272927676c715a6d6069756077273f276364697660272927666d776a68605a607d71606b766c6a6b5a7666776c7571273f275e58272927666a6b766a69605a696c6061273f27636469766027292762696a6764695a7364776c6467696076273f275e582729277672715a646971273f2763646976602729277f6b5a666475273f2763646976602729276d6a6e5a6b6a716c273f2763646976602729276c6b6f5a7f6367273f27636469766027292771273f27343636343334323c3d37323234272927676c715a75776a716a666a69273f2763646976602778; bit_env=7NCrRegY020LGVG5Yx8HFRWB73RARpFbj-iyQ1LwqU0cDI9moZj9ecPpsbpkSaMTEyZqsilIKiI_lt70BB_G6Dod7wN8rkLhE631Bz9wC_ixgEAlNeIdElXvK3C9gool9MEa3Y5xuHt4r36Y7HkF5YAELvmsxcB8412Lfy3XuXNgybsvbLqhJrUhs-rG5nU1V-xyc70ffKH2TqV_ZxyfiI1Qn7a3LENvJkf8V9ntSbLM3qoKcG5so8A6lMQ5LoyEsZgIq4i-rMHEO1Bc13y9wvk3oi-sJI76Ez-qeR_ArnBjdI6ZLTG_MUWfLeu9Ikz79n1nYgUl8r6sEXw3L3au4iOY5cfKhxFNEOszmGtoiAE8n91LvALTHWW_yZgi93E_ne4h-gOaqKLccAN05tCphxDc1uAoS3i4jBcKdnyF6ZVyGuJ_FSi4NQFvVGupfejzLbrfZoWDfGj6pgZpGEMCHnF0w_ajPy3jko_TKwdpi7DW6q49w-fjUYSjc3vJ137yj0N3um5dVKvIFJM1v0yBsavXNheto_S1GKCVq-6LTcM%3D; gulu_source_res=eyJwX2luIjoiOWYxNmJiYTEwNTIwMTgyMzIwOGMyZWYyYzllN2RkYWE1YjRjNTgzYmI0ZDhkYzAwNWNlODQxZjgwNTU3MzA5ZCJ9; passport_auth_mix_state=nt3zeeuup2eyy8cn750jdgpj52a9ldxlw3vzw45ba2eu8j77; is_dash_user=1; x-web-secsdk-uid=17063330-58d4-4719-9971-dba52fc661ab; __live_version__=%221.1.4.9549%22; has_avx2=null; device_web_cpu_core=16; device_web_memory_size=8; webcast_local_quality=null; live_use_vvc=%22false%22; csrf_session_id=5fe8f9d1180e55817920dae0808993ba; live_debug_info=%7B%22roomId%22%3A%227614515520083118863%22%2C%22resolution%22%3A%7B%22width%22%3A1920%2C%22height%22%3A1080%7D%2C%22fps%22%3A70%2C%22audioDataRate%22%3A48000%2C%22droppedFrames%22%3A4%2C%22totalFrames%22%3A65%2C%22videoBuffer%22%3A%5B%5D%2C%22src%22%3A%22https%3A%2F%2Fpull-flv-q13.douyincdn.com%2Fthirdgame%2Fstream-695437557938520894.flv%3Farch_hrchy%3Dh1%26exp_hrchy%3Dh1%26expire%3D1773502023%26major_anchor_level%3Dcommon%26sign%3D5d4807ba64265f674729e812ec33618c%26t_id%3D037-202603072327037BDC1553A514D5F37F8C-QZsvPZ%26unique_id%3Dstream-695437557938520894_830_flv%26_session_id%3D037-202603072327037BDC1553A514D5F37F8C-QZsvPZ.1772897224232.33396%26rsi%3D1%26abr_pts%3D-800%22%2C%22linkmicInfo%22%3A%7B%22uiLayout%22%3A0%2C%22playModes%22%3A%5B%5D%2C%22allDevices%22%3A%22%E8%BF%9E%E7%BA%BF%E8%AE%BE%E5%A4%87%EF%BC%9A%E7%94%B3%E8%AF%B7%E8%BF%9E%E7%BA%BF%E5%90%8E%E6%89%8D%E8%8E%B7%E5%8F%96%22%2C%22audioInputs%22%3A%5B%5D%2C%22videoInputs%22%3A%5B%5D%7D%2C%22href%22%3A%22https%3A%2F%2Flive.douyin.com%2F262229562462%3Fanchor_id%3D60708713854%26follow_status%3D0%26is_vs%3D0%26vs_ep_group_id%3D%26vs_episode_id%3D%26vs_episode_stage%3D%26vs_season_id%3D%22%7D; fpk1=U2FsdGVkX19Xphctu6x8/IFxEj3mGvQobR7U2Gy90RThMds9G7h1ZgbvhsMLPFfJL+8+eZ5CzEghbCVjENUCnA==; fpk2=800cce95768a9a4605cb3f6b181e9057; h265ErrorNum=-1; webcast_leading_last_show_time=1772897235315; webcast_leading_total_show_times=1; IsDouyinActive=false; live_can_add_dy_2_desktop=%220%22",
    }
    
    params = (
        "aid=6383&app_name=douyin_web&live_id=1&device_platform=web&"
        "browser_language=zh-CN&browser_platform=Win32&browser_name=Edge&"
        "browser_version=139.0.0.0&is_need_double_stream=false&web_rid=" + room_id
    )
    
    async with httpx.AsyncClient(timeout=15) as client:
        try:
            resp = await client.get(
                f"https://live.douyin.com/webcast/room/web/enter/?{params}",
                headers=headers,
            )
        except httpx.HTTPError as e:
            print(f"[LIVE] 抖音 API HTTP错误: {e}")
            return LiveStreamInfo(LiveStatus.ERROR, message=f"网络请求失败: {e}")
        
        print(f"[LIVE] 抖音 API 返回: HTTP {resp.status_code}")
        
        try:
            data = resp.json()
        except Exception:
            html_snippet = resp.text[:300].replace('\n', ' ')
            print(f"[LIVE] 抖音 API 非JSON响应: {html_snippet}")
            return LiveStreamInfo(LiveStatus.ERROR, message="抖音Cookie过期，API返回异常")
        
        if data.get("status_code") != 0:
            return LiveStreamInfo(LiveStatus.ABSENT, message="直播间不存在或未开播")
        
        try:
            room_data = data["data"]["data"][0]
            status = room_data["status"]
            
            if status != 2:
                return LiveStreamInfo(LiveStatus.NOT_LIVE, message="主播未开播")
            
            stream_url = room_data["stream_url"]
            
            # 尝试多种格式获取flv地址
            if "live_core_sdk_data" in stream_url:
                sdk_data = stream_url["live_core_sdk_data"]["pull_data"]
                stream_data = json.loads(sdk_data["stream_data"])
                flv_url = stream_data["data"]["origin"]["main"]["flv"]
                return LiveStreamInfo(LiveStatus.NORMAL, url=flv_url)
            
            if "pull_datas" in stream_url:
                pull_datas = stream_url["pull_datas"]
                if pull_datas:
                    first_pull = list(pull_datas.values())[0]
                    stream_data = json.loads(first_pull["stream_data"])
                    flv_url = stream_data["data"]["origin"]["main"]["flv"]
                    return LiveStreamInfo(LiveStatus.NORMAL, url=flv_url)
            
            return LiveStreamInfo(LiveStatus.ERROR, message="无法解析流地址")
            
        except (KeyError, IndexError) as e:
            return LiveStreamInfo(LiveStatus.ERROR, message=f"解析失败: {str(e)}")


async def get_stream_url(platform: LivePlatform, room_id: str) -> LiveStreamInfo:
    """统一接口：获取直播流地址"""
    if platform == LivePlatform.BILIBILI:
        return await get_bilibili_stream_url(room_id)
    elif platform == LivePlatform.DOUYIN:
        return await get_douyin_stream_url(room_id)
    return LiveStreamInfo(LiveStatus.ERROR, message="不支持的平台")


# === FFmpeg帧提取 ===

def extract_frames_from_url(
    stream_url: str,
    fps: float = 2.0,
    width: int = 640,
    height: int = 360
) -> subprocess.Popen:
    """启动FFmpeg进程从直播流提取帧，输出为raw RGB24数据到stdout"""
    args = [
        "ffmpeg",
        "-re",
        "-i", stream_url,
        "-vf", f"fps={fps},scale={width}:{height}",
        "-pix_fmt", "rgb24",
        "-vcodec", "rawvideo",
        "-an",
        "-sn",
        "-f", "rawvideo",
        "pipe:1"
    ]
    try:
        return subprocess.Popen(
            args,
            stdout=subprocess.PIPE,
            stderr=subprocess.DEVNULL,
            bufsize=width * height * 3
        )
    except FileNotFoundError:
        raise RuntimeError("FFmpeg未安装，请下载ffmpeg.exe并加入PATH，或放到项目目录下")


def read_frame(proc: subprocess.Popen, width: int, height: int) -> Optional[np.ndarray]:
    """从FFmpeg进程读取一帧，返回numpy数组(RGB格式)"""
    frame_size = width * height * 3
    data = proc.stdout.read(frame_size)
    if len(data) < frame_size:
        return None
    frame = np.frombuffer(data, dtype=np.uint8).reshape((height, width, 3))
    return frame


async def stream_frames(
    platform: LivePlatform,
    room_id: str,
    width: int = 640,
    height: int = 360,
    fps: float = 2.0
) -> AsyncIterator[np.ndarray | str]:
    """异步生成器：持续从直播流中提取帧
    
    Yields:
        np.ndarray: 一帧图像数据(RGB格式)
        str: 错误/状态信息 (以 "ERROR:" 或 "STATUS:" 开头)
    """
    info = await get_stream_url(platform, room_id)
    
    if info.status != LiveStatus.NORMAL:
        yield f"STATUS:{info.status.value}:{info.message}"
        return
    
    yield f"STATUS:{info.status.value}:直播流已连接"
    
    proc = extract_frames_from_url(info.url, fps, width, height)
    
    try:
        for _ in range(300):  # 最多5分钟
            frame = await asyncio.to_thread(read_frame, proc, width, height)
            if frame is None:
                yield "ERROR:直播流断开"
                break
            yield frame
    finally:
        proc.terminate()
        try:
            proc.wait(timeout=5)
        except subprocess.TimeoutExpired:
            proc.kill()
