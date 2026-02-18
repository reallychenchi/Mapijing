"""端到端实时语音对话服务配置."""

from dataclasses import dataclass, field
from typing import Any


@dataclass
class E2EConfig:
    """端到端实时语音对话服务配置.

    Attributes:
        app_id: 火山引擎 App ID
        access_key: 火山引擎 Access Key
        resource_id: 资源ID，固定值
        app_key: App Key，固定值
        base_url: WebSocket 连接地址
        model: 模型版本 (O, SC, 1.2.1.0, 2.2.0.0)
        speaker: TTS 发音人
        bot_name: 机器人名称
        system_role: 系统角色设定
        speaking_style: 说话风格
        output_audio_format: 输出音频格式 (pcm, pcm_s16le)
        output_sample_rate: 输出采样率
        end_smooth_window_ms: 判断用户停止说话的时间（毫秒）
        recv_timeout: 接收超时时间（秒）
    """

    app_id: str
    access_key: str
    resource_id: str = "volc.speech.dialog"
    app_key: str = "PlgvMymc7f3tQnJ6"
    base_url: str = "wss://openspeech.bytedance.com/api/v3/realtime/dialogue"

    # 模型配置
    model: str = "O"  # O, SC, 1.2.1.0, 2.2.0.0

    # TTS 配置
    speaker: str = "zh_female_vv_jupiter_bigtts"
    output_audio_format: str = "pcm"
    output_sample_rate: int = 24000

    # 对话配置
    bot_name: str = "小马"
    system_role: str = (
        "你是一个友善、温暖的AI助手，名叫小马。"
        "你善于倾听，能够给予用户情感支持和陪伴。"
    )
    speaking_style: str = "你的说话风格简洁明了，语速适中，语调自然，充满关怀。"

    # ASR 配置
    end_smooth_window_ms: int = 1500
    recv_timeout: int = 30  # 比默认10秒长一些，避免长对话中断

    # 额外配置
    strict_audit: bool = False
    location: dict[str, str] = field(default_factory=lambda: {"city": "北京", "country": "中国"})

    def get_ws_headers(self, connect_id: str) -> dict[str, str]:
        """获取 WebSocket 连接头部.

        Args:
            connect_id: 连接标识ID

        Returns:
            WebSocket 连接头部字典
        """
        return {
            "X-Api-App-ID": self.app_id,
            "X-Api-Access-Key": self.access_key,
            "X-Api-Resource-Id": self.resource_id,
            "X-Api-App-Key": self.app_key,
            "X-Api-Connect-Id": connect_id,
        }

    def get_start_session_payload(self, input_mod: str = "audio") -> dict[str, Any]:
        """获取 StartSession 事件的 payload.

        Args:
            input_mod: 输入模式 (audio, text, audio_file, keep_alive)

        Returns:
            StartSession payload 字典
        """
        payload = {
            "asr": {
                "extra": {
                    "end_smooth_window_ms": self.end_smooth_window_ms,
                },
            },
            "tts": {
                "speaker": self.speaker,
                "audio_config": {
                    "channel": 1,
                    "format": self.output_audio_format,
                    "sample_rate": self.output_sample_rate,
                },
            },
            "dialog": {
                "bot_name": self.bot_name,
                "system_role": self.system_role,
                "speaking_style": self.speaking_style,
                "location": self.location,
                "extra": {
                    "strict_audit": self.strict_audit,
                    "recv_timeout": self.recv_timeout,
                    "input_mod": input_mod,
                    "model": self.model,
                },
            },
        }
        return payload
