"""情感解析器 - 解析 LLM 返回的 XML 格式."""

import re
from dataclasses import dataclass


@dataclass
class ParsedResponse:
    """解析后的响应."""

    content: str  # 对话内容
    emotion: str  # 情感状态（中文）
    is_valid: bool  # 解析是否成功


class EmotionParser:
    """情感解析器."""

    VALID_EMOTIONS: list[str] = ["默认陪伴", "共情倾听", "安慰支持", "轻松愉悦"]
    DEFAULT_EMOTION: str = "默认陪伴"

    # 正则表达式
    CONTENT_PATTERN: re.Pattern[str] = re.compile(
        r"<content>(.*?)</content>", re.DOTALL
    )
    EMOTION_PATTERN: re.Pattern[str] = re.compile(
        r"<emotion>(.*?)</emotion>", re.DOTALL
    )

    def parse(self, raw_response: str) -> ParsedResponse:
        """
        解析 LLM 响应.

        Args:
            raw_response: LLM 原始返回文本

        Returns:
            ParsedResponse 对象
        """
        content = self._extract_content(raw_response)
        emotion = self._extract_emotion(raw_response)

        return ParsedResponse(
            content=content,
            emotion=emotion,
            is_valid=bool(content),  # content 不为空即认为有效
        )

    def _extract_content(self, raw: str) -> str:
        """提取 content 标签内容."""
        match = self.CONTENT_PATTERN.search(raw)
        if match:
            return match.group(1).strip()

        # 兜底：如果没有标签，返回整个响应（去除可能的 emotion 标签）
        fallback = self.EMOTION_PATTERN.sub("", raw).strip()
        return fallback if fallback else raw.strip()

    def _extract_emotion(self, raw: str) -> str:
        """提取 emotion 标签内容."""
        match = self.EMOTION_PATTERN.search(raw)
        if match:
            emotion = match.group(1).strip()
            # 验证情感值是否有效
            if emotion in self.VALID_EMOTIONS:
                return emotion

        # 默认返回 "默认陪伴"
        return self.DEFAULT_EMOTION
