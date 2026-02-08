"""对话上下文管理器."""

from dataclasses import dataclass, field


@dataclass
class Message:
    """对话消息."""

    role: str  # "user" | "assistant"
    content: str  # 消息内容


@dataclass
class ContextConfig:
    """上下文配置."""

    max_tokens: int = 50000  # 最大 token 数
    chars_per_token: float = 1.5  # 中文约 1.5 字符/token
    min_history_count: int = 2  # 至少保留的对话轮数


@dataclass
class ContextManager:
    """对话上下文管理器."""

    config: ContextConfig = field(default_factory=ContextConfig)
    messages: list[Message] = field(default_factory=list)

    def add_user_message(self, content: str) -> None:
        """添加用户消息."""
        self.messages.append(Message(role="user", content=content))
        self._trim_if_needed()

    def add_assistant_message(self, content: str) -> None:
        """添加助手消息."""
        self.messages.append(Message(role="assistant", content=content))
        self._trim_if_needed()

    def get_messages(self) -> list[dict[str, str]]:
        """获取消息列表（API 格式）."""
        return [{"role": m.role, "content": m.content} for m in self.messages]

    def clear(self) -> None:
        """清空上下文."""
        self.messages.clear()

    def estimate_tokens(self) -> int:
        """估算当前 token 数."""
        total_chars = sum(len(m.content) for m in self.messages)
        return int(total_chars / self.config.chars_per_token)

    def _trim_if_needed(self) -> None:
        """如果超过限制，截断早期消息."""
        while (
            self.estimate_tokens() > self.config.max_tokens
            and len(self.messages) > self.config.min_history_count * 2
        ):
            # 删除最早的一轮对话（user + assistant）
            self.messages.pop(0)
            if self.messages and self.messages[0].role == "assistant":
                self.messages.pop(0)

    def get_message_count(self) -> int:
        """获取消息数量."""
        return len(self.messages)
