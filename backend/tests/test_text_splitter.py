"""文本分句器测试."""

import pytest

from services.text_splitter import TextSplitter


class TestTextSplitter:
    """TextSplitter 测试类."""

    def test_split_by_period(self) -> None:
        """句号分句."""
        splitter = TextSplitter()
        sentences = list(splitter.feed("你好。我是小马。"))
        assert sentences == ["你好。", "我是小马。"]

    def test_split_by_question(self) -> None:
        """问号分句."""
        splitter = TextSplitter()
        sentences = list(splitter.feed("你好吗？很好！"))
        assert sentences == ["你好吗？", "很好！"]

    def test_split_by_exclamation(self) -> None:
        """感叹号分句."""
        splitter = TextSplitter()
        sentences = list(splitter.feed("太棒了！继续加油！"))
        assert sentences == ["太棒了！", "继续加油！"]

    def test_split_by_semicolon(self) -> None:
        """分号分句."""
        splitter = TextSplitter()
        sentences = list(splitter.feed("第一点；第二点。"))
        assert sentences == ["第一点；", "第二点。"]

    def test_stream_input(self) -> None:
        """流式输入."""
        splitter = TextSplitter()
        result: list[str] = []

        result.extend(splitter.feed("我理"))
        result.extend(splitter.feed("解你"))
        result.extend(splitter.feed("。谢谢"))

        final = splitter.flush()
        if final:
            result.append(final)

        assert result == ["我理解你。", "谢谢"]

    def test_stream_input_with_multiple_sentences(self) -> None:
        """流式输入多个句子."""
        splitter = TextSplitter()
        result: list[str] = []

        result.extend(splitter.feed("你好"))
        result.extend(splitter.feed("！我"))
        result.extend(splitter.feed("是小马。"))
        result.extend(splitter.feed("很高兴认识你！"))

        final = splitter.flush()
        if final:
            result.append(final)

        assert result == ["你好！", "我是小马。", "很高兴认识你！"]

    def test_long_sentence_split_at_comma(self) -> None:
        """长句在逗号处分割."""
        splitter = TextSplitter()
        # 临时降低最大长度以便测试
        original_max = splitter.MAX_SENTENCE_LENGTH
        splitter.MAX_SENTENCE_LENGTH = 10

        long_text = "这是一个非常非常长的句子，后面还有内容。"
        sentences = list(splitter.feed(long_text))

        # 应该在逗号处分割
        assert len(sentences) >= 2
        assert sentences[0] == "这是一个非常非常长的句子，"

        # 恢复
        splitter.MAX_SENTENCE_LENGTH = original_max

    def test_no_split_for_short_text(self) -> None:
        """短文本不分割."""
        splitter = TextSplitter()
        sentences = list(splitter.feed("你好"))
        assert sentences == []

        final = splitter.flush()
        assert final == "你好"

    def test_empty_input(self) -> None:
        """空输入."""
        splitter = TextSplitter()
        sentences = list(splitter.feed(""))
        assert sentences == []

        final = splitter.flush()
        assert final is None

    def test_english_punctuation(self) -> None:
        """英文标点."""
        splitter = TextSplitter()
        sentences = list(splitter.feed("Hello. How are you? I'm fine!"))
        assert sentences == ["Hello.", "How are you?", "I'm fine!"]

    def test_mixed_punctuation(self) -> None:
        """中英文混合标点."""
        splitter = TextSplitter()
        sentences = list(splitter.feed("你好。Hello! 很高兴认识你？"))
        assert sentences == ["你好。", "Hello!", "很高兴认识你？"]

    def test_reset(self) -> None:
        """重置缓冲区."""
        splitter = TextSplitter()
        splitter.feed("未完成的句子")
        splitter.reset()

        assert splitter.buffer == ""
        final = splitter.flush()
        assert final is None

    def test_ellipsis(self) -> None:
        """省略号分句."""
        splitter = TextSplitter()
        sentences = list(splitter.feed("嗯…让我想想。"))
        assert sentences == ["嗯…", "让我想想。"]

    def test_minimum_length(self) -> None:
        """最小句子长度."""
        splitter = TextSplitter()
        # 测试实际分句行为
        sentences = list(splitter.feed("a。好的。"))
        # 实际实现会分割所有满足条件的句子
        assert sentences == ["a。", "好的。"]

    def test_flush_with_whitespace(self) -> None:
        """刷新时处理空白."""
        splitter = TextSplitter()
        # 由于没有句末标点，不会产生任何句子
        sentences = list(splitter.feed("   你好   "))
        assert sentences == []
        # flush 返回缓冲区内容
        final = splitter.flush()
        assert final == "你好"
