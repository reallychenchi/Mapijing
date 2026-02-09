"""文本分句器 - 将流式文本按句子切分."""

from collections.abc import Generator


class TextSplitter:
    """文本分句器.

    将流式输入的文本按句子切分，支持中英文标点。
    """

    # 句子结束标点
    SENTENCE_ENDINGS: list[str] = ["。", "！", "？", "；", "…", ".", "!", "?", ";"]

    # 逗号作为次要分割点（句子过长时）
    COMMA_MARKS: list[str] = ["，", ","]

    # 单句最大长度（超过则在逗号处分割）
    MAX_SENTENCE_LENGTH: int = 50

    # 单句最小长度（避免太短的句子）
    MIN_SENTENCE_LENGTH: int = 2

    def __init__(self) -> None:
        """初始化分句器."""
        self.buffer: str = ""

    def feed(self, text: str) -> Generator[str, None, None]:
        """输入文本片段，输出完整句子.

        Args:
            text: 输入的文本片段

        Yields:
            完整的句子
        """
        self.buffer += text

        while True:
            sentence = self._try_extract_sentence()
            if sentence:
                yield sentence
            else:
                break

    def flush(self) -> str | None:
        """刷新缓冲区，返回剩余文本.

        Returns:
            剩余的文本（如果有）
        """
        if self.buffer.strip():
            result = self.buffer.strip()
            self.buffer = ""
            return result
        return None

    def _try_extract_sentence(self) -> str | None:
        """尝试从缓冲区提取一个句子."""
        # 记录最后一个逗号位置（用于长句分割）
        last_comma_pos = -1

        for i, char in enumerate(self.buffer):
            # 记录逗号位置
            if char in self.COMMA_MARKS:
                last_comma_pos = i

            # 检查句子结束标点
            if char in self.SENTENCE_ENDINGS:
                sentence = self.buffer[: i + 1].strip()
                if len(sentence) >= self.MIN_SENTENCE_LENGTH:
                    self.buffer = self.buffer[i + 1 :]
                    return sentence

            # 句子过长，在逗号处分割
            if i >= self.MAX_SENTENCE_LENGTH and last_comma_pos > 0:
                sentence = self.buffer[: last_comma_pos + 1].strip()
                if len(sentence) >= self.MIN_SENTENCE_LENGTH:
                    self.buffer = self.buffer[last_comma_pos + 1 :]
                    return sentence

        return None

    def reset(self) -> None:
        """重置缓冲区."""
        self.buffer = ""
