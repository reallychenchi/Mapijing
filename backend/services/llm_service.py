"""LLM 服务 - DeepSeek API 调用."""

from collections.abc import AsyncGenerator
from dataclasses import dataclass

import httpx

from services.emotion_parser import EmotionParser, ParsedResponse


@dataclass
class LLMConfig:
    """LLM 配置."""

    api_url: str = "https://api.deepseek.com/chat/completions"
    api_key: str = ""
    model: str = "deepseek-chat"
    max_tokens: int = 2048
    temperature: float = 0.7


@dataclass
class LLMResponse:
    """LLM 响应结构."""

    content: str  # 对话内容
    emotion: str  # 情感状态
    raw_response: str  # 原始响应（调试用）


class LLMService:
    """DeepSeek LLM 服务."""

    SYSTEM_PROMPT: str = (
        "你是一个善解人意的小马，帮助对方聊天。"
        "返回格式要求用 <content> </content> <emotion></emotion> 标签标记，"
        "content中间是返回的对话，emotion中间是当前小马的表情，"
        "有 默认陪伴、共情倾听、安慰支持、轻松愉悦 四种，其中 默认陪伴 是默认状态。"
    )

    def __init__(self, config: LLMConfig) -> None:
        """
        初始化 LLM 服务.

        Args:
            config: LLM 配置
        """
        self.config = config
        self.client = httpx.AsyncClient(timeout=60.0)
        self._parser = EmotionParser()

    async def chat(
        self,
        messages: list[dict[str, str]],
        stream: bool = False,
    ) -> LLMResponse | AsyncGenerator[str, None]:
        """
        发送对话请求.

        Args:
            messages: 对话历史 [{"role": "user", "content": "..."}]
            stream: 是否流式返回

        Returns:
            非流式: LLMResponse 对象
            流式: 异步生成器，逐字返回
        """
        if stream:
            return self.chat_stream(messages)
        return await self.chat_non_stream(messages)

    async def chat_non_stream(self, messages: list[dict[str, str]]) -> LLMResponse:
        """
        非流式对话（本阶段使用）.

        Args:
            messages: 对话历史

        Returns:
            LLMResponse 对象
        """
        # 构建请求体
        full_messages = [
            {"role": "system", "content": self.SYSTEM_PROMPT},
            *messages,
        ]

        payload = {
            "model": self.config.model,
            "messages": full_messages,
            "stream": False,
            "max_tokens": self.config.max_tokens,
            "temperature": self.config.temperature,
        }

        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {self.config.api_key}",
        }

        response = await self.client.post(
            self.config.api_url,
            json=payload,
            headers=headers,
        )
        response.raise_for_status()

        data = response.json()
        raw_content = data["choices"][0]["message"]["content"]

        # 解析响应
        return self._parse_response(raw_content)

    async def chat_stream(
        self, messages: list[dict[str, str]]
    ) -> AsyncGenerator[str, None]:
        """
        流式对话（阶段5使用，预留接口）.

        Args:
            messages: 对话历史

        Yields:
            逐字返回文本
        """
        # 构建请求体
        full_messages = [
            {"role": "system", "content": self.SYSTEM_PROMPT},
            *messages,
        ]

        payload = {
            "model": self.config.model,
            "messages": full_messages,
            "stream": True,
            "max_tokens": self.config.max_tokens,
            "temperature": self.config.temperature,
        }

        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {self.config.api_key}",
        }

        async with self.client.stream(
            "POST",
            self.config.api_url,
            json=payload,
            headers=headers,
        ) as response:
            response.raise_for_status()
            async for line in response.aiter_lines():
                if line.startswith("data: "):
                    data = line[6:]
                    if data == "[DONE]":
                        break
                    import json

                    chunk = json.loads(data)
                    delta = chunk.get("choices", [{}])[0].get("delta", {})
                    content = delta.get("content", "")
                    if content:
                        yield content

    def _parse_response(self, raw: str) -> LLMResponse:
        """
        解析 LLM 响应，提取 content 和 emotion.

        Args:
            raw: 原始响应文本

        Returns:
            LLMResponse 对象
        """
        parsed: ParsedResponse = self._parser.parse(raw)
        return LLMResponse(
            content=parsed.content,
            emotion=parsed.emotion,
            raw_response=raw,
        )

    async def close(self) -> None:
        """关闭 HTTP 客户端."""
        await self.client.aclose()
