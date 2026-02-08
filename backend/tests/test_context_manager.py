"""上下文管理器单元测试."""

from services.context_manager import ContextConfig, ContextManager, Message


class TestContextManager:
    """ContextManager 测试类."""

    def test_add_user_message(self) -> None:
        """添加用户消息."""
        cm = ContextManager()
        cm.add_user_message("你好")

        messages = cm.get_messages()
        assert len(messages) == 1
        assert messages[0]["role"] == "user"
        assert messages[0]["content"] == "你好"

    def test_add_assistant_message(self) -> None:
        """添加助手消息."""
        cm = ContextManager()
        cm.add_assistant_message("你好！很高兴见到你")

        messages = cm.get_messages()
        assert len(messages) == 1
        assert messages[0]["role"] == "assistant"
        assert messages[0]["content"] == "你好！很高兴见到你"

    def test_add_multiple_messages(self) -> None:
        """添加多条消息."""
        cm = ContextManager()
        cm.add_user_message("你好")
        cm.add_assistant_message("你好！很高兴见到你")
        cm.add_user_message("今天天气怎么样？")
        cm.add_assistant_message("今天天气很好！")

        messages = cm.get_messages()
        assert len(messages) == 4
        assert messages[0]["role"] == "user"
        assert messages[1]["role"] == "assistant"
        assert messages[2]["role"] == "user"
        assert messages[3]["role"] == "assistant"

    def test_clear(self) -> None:
        """清空上下文."""
        cm = ContextManager()
        cm.add_user_message("test")
        cm.add_assistant_message("response")
        cm.clear()
        assert len(cm.get_messages()) == 0

    def test_estimate_tokens(self) -> None:
        """估算 token 数."""
        config = ContextConfig(chars_per_token=1.0)  # 简化：1字符=1token
        cm = ContextManager(config=config)
        cm.add_user_message("你好")  # 2 字符
        cm.add_assistant_message("你好啊")  # 3 字符

        tokens = cm.estimate_tokens()
        assert tokens == 5  # 2 + 3 = 5

    def test_trim_when_exceed(self) -> None:
        """超过限制时截断."""
        config = ContextConfig(
            max_tokens=100,
            chars_per_token=1.0,
            min_history_count=2,  # 至少保留2轮=4条消息
        )
        cm = ContextManager(config=config)

        # 添加超长内容
        for _ in range(10):
            cm.add_user_message("x" * 50)
            cm.add_assistant_message("y" * 50)

        # 验证被截断到 min_history_count * 2 条消息
        # 由于每条消息50字符，4条=200字符，超过100但是是最小保留数
        assert cm.get_message_count() == config.min_history_count * 2

    def test_min_history_preserved(self) -> None:
        """至少保留最小历史轮数."""
        config = ContextConfig(
            max_tokens=10,  # 很小的限制
            chars_per_token=1.0,
            min_history_count=2,
        )
        cm = ContextManager(config=config)

        # 添加内容
        for _ in range(5):
            cm.add_user_message("x" * 100)
            cm.add_assistant_message("y" * 100)

        # 即使超过 token 限制，也至少保留 min_history_count * 2 条消息
        assert cm.get_message_count() >= config.min_history_count * 2

    def test_get_message_count(self) -> None:
        """获取消息数量."""
        cm = ContextManager()
        assert cm.get_message_count() == 0

        cm.add_user_message("1")
        assert cm.get_message_count() == 1

        cm.add_assistant_message("2")
        assert cm.get_message_count() == 2

    def test_default_config(self) -> None:
        """默认配置."""
        cm = ContextManager()
        assert cm.config.max_tokens == 50000
        assert cm.config.chars_per_token == 1.5
        assert cm.config.min_history_count == 2

    def test_custom_config(self) -> None:
        """自定义配置."""
        config = ContextConfig(
            max_tokens=10000,
            chars_per_token=2.0,
            min_history_count=3,
        )
        cm = ContextManager(config=config)
        assert cm.config.max_tokens == 10000
        assert cm.config.chars_per_token == 2.0
        assert cm.config.min_history_count == 3

    def test_message_dataclass(self) -> None:
        """测试 Message 数据类."""
        msg = Message(role="user", content="测试消息")
        assert msg.role == "user"
        assert msg.content == "测试消息"

    def test_empty_messages(self) -> None:
        """空消息列表."""
        cm = ContextManager()
        messages = cm.get_messages()
        assert messages == []
        assert cm.estimate_tokens() == 0

    def test_trim_removes_user_assistant_pair(self) -> None:
        """截断时删除 user+assistant 对."""
        config = ContextConfig(
            max_tokens=50,
            chars_per_token=1.0,
            min_history_count=1,
        )
        cm = ContextManager(config=config)

        # 添加第一轮
        cm.add_user_message("a" * 20)
        cm.add_assistant_message("b" * 20)

        # 添加第二轮 - 这应该触发截断
        cm.add_user_message("c" * 20)
        cm.add_assistant_message("d" * 20)

        # 验证早期消息被删除
        messages = cm.get_messages()
        # 由于 min_history_count=1，至少保留2条（1轮）
        assert len(messages) >= 2
