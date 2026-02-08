"""情感解析器单元测试."""

from services.emotion_parser import EmotionParser, ParsedResponse


class TestEmotionParser:
    """EmotionParser 测试类."""

    def setup_method(self) -> None:
        """初始化测试."""
        self.parser = EmotionParser()

    def test_normal_format(self) -> None:
        """正常格式解析."""
        raw = "<content>我理解你的感受</content><emotion>共情倾听</emotion>"
        result = self.parser.parse(raw)
        assert result.content == "我理解你的感受"
        assert result.emotion == "共情倾听"
        assert result.is_valid is True

    def test_normal_format_with_comfort(self) -> None:
        """正常格式解析 - 安慰支持."""
        raw = "<content>别担心，一切都会好起来的</content><emotion>安慰支持</emotion>"
        result = self.parser.parse(raw)
        assert result.content == "别担心，一切都会好起来的"
        assert result.emotion == "安慰支持"
        assert result.is_valid is True

    def test_normal_format_with_happy(self) -> None:
        """正常格式解析 - 轻松愉悦."""
        raw = "<content>哈哈，这个笑话真好笑！</content><emotion>轻松愉悦</emotion>"
        result = self.parser.parse(raw)
        assert result.content == "哈哈，这个笑话真好笑！"
        assert result.emotion == "轻松愉悦"
        assert result.is_valid is True

    def test_missing_emotion(self) -> None:
        """缺少 emotion 标签."""
        raw = "<content>你好</content>"
        result = self.parser.parse(raw)
        assert result.content == "你好"
        assert result.emotion == "默认陪伴"
        assert result.is_valid is True

    def test_invalid_emotion(self) -> None:
        """无效的情感值."""
        raw = "<content>哈哈</content><emotion>开心</emotion>"
        result = self.parser.parse(raw)
        assert result.content == "哈哈"
        assert result.emotion == "默认陪伴"  # 无效值回退到默认
        assert result.is_valid is True

    def test_no_tags(self) -> None:
        """完全无标签."""
        raw = "你好，我是小马"
        result = self.parser.parse(raw)
        assert result.content == "你好，我是小马"
        assert result.emotion == "默认陪伴"
        assert result.is_valid is True

    def test_multiline_content(self) -> None:
        """多行内容."""
        raw = "<content>第一行\n第二行</content><emotion>安慰支持</emotion>"
        result = self.parser.parse(raw)
        assert "第一行" in result.content
        assert "第二行" in result.content
        assert result.emotion == "安慰支持"
        assert result.is_valid is True

    def test_content_with_whitespace(self) -> None:
        """内容有前后空白."""
        raw = "<content>  你好啊  </content><emotion>默认陪伴</emotion>"
        result = self.parser.parse(raw)
        assert result.content == "你好啊"  # 应该被 strip
        assert result.emotion == "默认陪伴"

    def test_emotion_with_whitespace(self) -> None:
        """情感值有前后空白."""
        raw = "<content>你好</content><emotion>  共情倾听  </emotion>"
        result = self.parser.parse(raw)
        assert result.emotion == "共情倾听"  # 应该被 strip

    def test_empty_content(self) -> None:
        """空内容."""
        raw = "<content></content><emotion>默认陪伴</emotion>"
        result = self.parser.parse(raw)
        assert result.content == ""
        assert result.is_valid is False  # 空内容无效

    def test_only_emotion_tag(self) -> None:
        """只有 emotion 标签 - 内容使用兜底逻辑."""
        raw = "<emotion>共情倾听</emotion>"
        result = self.parser.parse(raw)
        # 兜底逻辑：没有 content 标签时，返回去除 emotion 标签后的原始内容
        # 如果去除后为空，则返回原始内容
        assert result.content == "<emotion>共情倾听</emotion>"  # 去除后为空，返回原始
        assert result.emotion == "共情倾听"
        assert result.is_valid is True  # 有内容就是有效的

    def test_reversed_tags_order(self) -> None:
        """标签顺序颠倒."""
        raw = "<emotion>安慰支持</emotion><content>我在这里陪你</content>"
        result = self.parser.parse(raw)
        assert result.content == "我在这里陪你"
        assert result.emotion == "安慰支持"
        assert result.is_valid is True

    def test_extra_text_outside_tags(self) -> None:
        """标签外有额外文字."""
        raw = "前缀文字<content>核心内容</content>中间文字<emotion>轻松愉悦</emotion>后缀文字"
        result = self.parser.parse(raw)
        assert result.content == "核心内容"
        assert result.emotion == "轻松愉悦"

    def test_all_valid_emotions(self) -> None:
        """测试所有有效情感值."""
        valid_emotions = ["默认陪伴", "共情倾听", "安慰支持", "轻松愉悦"]
        for emotion in valid_emotions:
            raw = f"<content>测试</content><emotion>{emotion}</emotion>"
            result = self.parser.parse(raw)
            assert result.emotion == emotion

    def test_parsed_response_dataclass(self) -> None:
        """测试 ParsedResponse 数据类."""
        response = ParsedResponse(
            content="测试内容",
            emotion="共情倾听",
            is_valid=True,
        )
        assert response.content == "测试内容"
        assert response.emotion == "共情倾听"
        assert response.is_valid is True
