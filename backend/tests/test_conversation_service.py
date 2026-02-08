"""会话服务单元测试."""

from unittest.mock import AsyncMock, patch

import pytest

from services.context_manager import ContextConfig
from services.conversation_service import ConversationConfig, ConversationService
from services.llm_service import LLMConfig, LLMResponse


class TestConversationConfig:
    """ConversationConfig 测试类."""

    def test_config_with_llm_config(self) -> None:
        """配置包含 LLM 配置."""
        llm_config = LLMConfig(api_key="test_key")
        config = ConversationConfig(llm_config=llm_config)
        assert config.llm_config.api_key == "test_key"

    def test_config_with_context_config(self) -> None:
        """配置包含上下文配置."""
        llm_config = LLMConfig(api_key="test_key")
        context_config = ContextConfig(max_tokens=10000)
        config = ConversationConfig(
            llm_config=llm_config,
            context_config=context_config,
        )
        assert config.context_config.max_tokens == 10000


class TestConversationService:
    """ConversationService 测试类."""

    def setup_method(self) -> None:
        """初始化测试."""
        self.llm_config = LLMConfig(api_key="test_key")
        self.config = ConversationConfig(llm_config=self.llm_config)

    def test_init(self) -> None:
        """初始化服务."""
        service = ConversationService(self.config)
        assert service.current_emotion == "默认陪伴"
        assert service.context_manager.get_message_count() == 0

    def test_get_current_emotion(self) -> None:
        """获取当前情感."""
        service = ConversationService(self.config)
        assert service.get_current_emotion() == "默认陪伴"

    def test_reset(self) -> None:
        """重置会话."""
        service = ConversationService(self.config)
        service.context_manager.add_user_message("测试")
        service.current_emotion = "共情倾听"

        service.reset()

        assert service.context_manager.get_message_count() == 0
        assert service.current_emotion == "默认陪伴"

    @pytest.mark.asyncio
    async def test_process_user_input(self) -> None:
        """处理用户输入."""
        service = ConversationService(self.config)

        mock_response = LLMResponse(
            content="你好啊",
            emotion="默认陪伴",
            raw_response="<content>你好啊</content><emotion>默认陪伴</emotion>",
        )

        with patch.object(
            service.llm_service,
            "chat_non_stream",
            new_callable=AsyncMock,
            return_value=mock_response,
        ):
            result = await service.process_user_input("你好")

            assert result == "你好啊"
            # 验证消息被添加到上下文
            messages = service.context_manager.get_messages()
            assert len(messages) == 2
            assert messages[0]["role"] == "user"
            assert messages[0]["content"] == "你好"
            assert messages[1]["role"] == "assistant"
            assert messages[1]["content"] == "你好啊"

        await service.close()

    @pytest.mark.asyncio
    async def test_process_user_input_emotion_change(self) -> None:
        """处理用户输入 - 情感变化."""
        service = ConversationService(self.config)

        mock_response = LLMResponse(
            content="我理解你的感受",
            emotion="共情倾听",
            raw_response="<content>我理解你的感受</content><emotion>共情倾听</emotion>",
        )

        emotion_callback = AsyncMock()

        with patch.object(
            service.llm_service,
            "chat_non_stream",
            new_callable=AsyncMock,
            return_value=mock_response,
        ):
            await service.process_user_input(
                "我今天心情不好",
                on_emotion_change=emotion_callback,
            )

            # 验证情感回调被调用
            emotion_callback.assert_called_once_with("共情倾听")
            assert service.current_emotion == "共情倾听"

        await service.close()

    @pytest.mark.asyncio
    async def test_process_user_input_no_emotion_change(self) -> None:
        """处理用户输入 - 无情感变化."""
        service = ConversationService(self.config)

        mock_response = LLMResponse(
            content="你好",
            emotion="默认陪伴",  # 和初始状态相同
            raw_response="<content>你好</content><emotion>默认陪伴</emotion>",
        )

        emotion_callback = AsyncMock()

        with patch.object(
            service.llm_service,
            "chat_non_stream",
            new_callable=AsyncMock,
            return_value=mock_response,
        ):
            await service.process_user_input(
                "你好",
                on_emotion_change=emotion_callback,
            )

            # 情感没变化，回调不应该被调用
            emotion_callback.assert_not_called()

        await service.close()

    @pytest.mark.asyncio
    async def test_process_user_input_llm_callback(self) -> None:
        """处理用户输入 - LLM 回复回调."""
        service = ConversationService(self.config)

        mock_response = LLMResponse(
            content="测试回复",
            emotion="默认陪伴",
            raw_response="<content>测试回复</content><emotion>默认陪伴</emotion>",
        )

        llm_callback = AsyncMock()

        with patch.object(
            service.llm_service,
            "chat_non_stream",
            new_callable=AsyncMock,
            return_value=mock_response,
        ):
            await service.process_user_input(
                "测试",
                on_llm_response=llm_callback,
            )

            llm_callback.assert_called_once_with("测试回复")

        await service.close()

    @pytest.mark.asyncio
    async def test_process_user_input_all_callbacks(self) -> None:
        """处理用户输入 - 所有回调."""
        service = ConversationService(self.config)

        mock_response = LLMResponse(
            content="我在这里",
            emotion="安慰支持",
            raw_response="<content>我在这里</content><emotion>安慰支持</emotion>",
        )

        emotion_callback = AsyncMock()
        llm_callback = AsyncMock()

        with patch.object(
            service.llm_service,
            "chat_non_stream",
            new_callable=AsyncMock,
            return_value=mock_response,
        ):
            result = await service.process_user_input(
                "我很难过",
                on_emotion_change=emotion_callback,
                on_llm_response=llm_callback,
            )

            assert result == "我在这里"
            emotion_callback.assert_called_once_with("安慰支持")
            llm_callback.assert_called_once_with("我在这里")

        await service.close()

    @pytest.mark.asyncio
    async def test_multi_turn_conversation(self) -> None:
        """多轮对话."""
        service = ConversationService(self.config)

        responses = [
            LLMResponse(
                content="你好小明",
                emotion="默认陪伴",
                raw_response="<content>你好小明</content><emotion>默认陪伴</emotion>",
            ),
            LLMResponse(
                content="你是小明",
                emotion="轻松愉悦",
                raw_response="<content>你是小明</content><emotion>轻松愉悦</emotion>",
            ),
        ]

        with patch.object(
            service.llm_service,
            "chat_non_stream",
            new_callable=AsyncMock,
            side_effect=responses,
        ):
            await service.process_user_input("我叫小明")
            await service.process_user_input("你还记得我叫什么吗")

            # 验证上下文包含所有消息
            messages = service.context_manager.get_messages()
            assert len(messages) == 4
            assert messages[0]["content"] == "我叫小明"
            assert messages[1]["content"] == "你好小明"
            assert messages[2]["content"] == "你还记得我叫什么吗"
            assert messages[3]["content"] == "你是小明"

        await service.close()

    @pytest.mark.asyncio
    async def test_close(self) -> None:
        """关闭服务."""
        service = ConversationService(self.config)

        with patch.object(
            service.llm_service, "close", new_callable=AsyncMock
        ) as mock_close:
            await service.close()
            mock_close.assert_called_once()
