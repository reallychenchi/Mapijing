"""LLM 服务单元测试."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from services.llm_service import LLMConfig, LLMResponse, LLMService


class TestLLMConfig:
    """LLMConfig 测试类."""

    def test_default_config(self) -> None:
        """默认配置."""
        config = LLMConfig()
        assert config.api_url == "https://api.deepseek.com/chat/completions"
        assert config.api_key == ""
        assert config.model == "deepseek-chat"
        assert config.max_tokens == 2048
        assert config.temperature == 0.7

    def test_custom_config(self) -> None:
        """自定义配置."""
        config = LLMConfig(
            api_url="https://custom.api.com",
            api_key="test_key",
            model="custom-model",
            max_tokens=4096,
            temperature=0.5,
        )
        assert config.api_url == "https://custom.api.com"
        assert config.api_key == "test_key"
        assert config.model == "custom-model"
        assert config.max_tokens == 4096
        assert config.temperature == 0.5


class TestLLMResponse:
    """LLMResponse 测试类."""

    def test_response_dataclass(self) -> None:
        """测试 LLMResponse 数据类."""
        response = LLMResponse(
            content="你好",
            emotion="默认陪伴",
            raw_response="<content>你好</content><emotion>默认陪伴</emotion>",
        )
        assert response.content == "你好"
        assert response.emotion == "默认陪伴"
        assert "<content>" in response.raw_response


class TestLLMService:
    """LLMService 测试类."""

    def test_system_prompt(self) -> None:
        """系统提示词."""
        assert "小马" in LLMService.SYSTEM_PROMPT
        assert "content" in LLMService.SYSTEM_PROMPT
        assert "emotion" in LLMService.SYSTEM_PROMPT
        assert "默认陪伴" in LLMService.SYSTEM_PROMPT

    @pytest.mark.asyncio
    async def test_chat_non_stream(self) -> None:
        """非流式对话."""
        config = LLMConfig(api_key="test_key")
        service = LLMService(config)

        # Mock HTTP 响应
        mock_response = MagicMock()
        mock_response.json.return_value = {
            "choices": [
                {
                    "message": {
                        "content": "<content>你好</content><emotion>默认陪伴</emotion>"
                    }
                }
            ]
        }
        mock_response.raise_for_status = MagicMock()

        with patch.object(
            service.client, "post", new_callable=AsyncMock
        ) as mock_post:
            mock_post.return_value = mock_response

            result = await service.chat_non_stream(
                [{"role": "user", "content": "你好"}]
            )

            assert result.content == "你好"
            assert result.emotion == "默认陪伴"

            # 验证请求参数
            call_args = mock_post.call_args
            assert call_args[1]["json"]["model"] == "deepseek-chat"
            assert call_args[1]["json"]["stream"] is False
            assert len(call_args[1]["json"]["messages"]) == 2  # system + user

        await service.close()

    @pytest.mark.asyncio
    async def test_chat_non_stream_with_empathy(self) -> None:
        """非流式对话 - 共情倾听."""
        config = LLMConfig(api_key="test_key")
        service = LLMService(config)

        mock_response = MagicMock()
        mock_response.json.return_value = {
            "choices": [
                {
                    "message": {
                        "content": "<content>我理解你的感受</content><emotion>共情倾听</emotion>"
                    }
                }
            ]
        }
        mock_response.raise_for_status = MagicMock()

        with patch.object(
            service.client, "post", new_callable=AsyncMock
        ) as mock_post:
            mock_post.return_value = mock_response

            result = await service.chat_non_stream(
                [{"role": "user", "content": "我今天心情不好"}]
            )

            assert result.content == "我理解你的感受"
            assert result.emotion == "共情倾听"

        await service.close()

    @pytest.mark.asyncio
    async def test_chat_non_stream_no_tags(self) -> None:
        """非流式对话 - 无标签响应."""
        config = LLMConfig(api_key="test_key")
        service = LLMService(config)

        mock_response = MagicMock()
        mock_response.json.return_value = {
            "choices": [{"message": {"content": "你好，我是小马"}}]
        }
        mock_response.raise_for_status = MagicMock()

        with patch.object(
            service.client, "post", new_callable=AsyncMock
        ) as mock_post:
            mock_post.return_value = mock_response

            result = await service.chat_non_stream(
                [{"role": "user", "content": "你是谁"}]
            )

            assert result.content == "你好，我是小马"
            assert result.emotion == "默认陪伴"  # 默认情感

        await service.close()

    @pytest.mark.asyncio
    async def test_chat_method_non_stream(self) -> None:
        """chat 方法非流式调用."""
        config = LLMConfig(api_key="test_key")
        service = LLMService(config)

        mock_response = MagicMock()
        mock_response.json.return_value = {
            "choices": [
                {
                    "message": {
                        "content": "<content>测试</content><emotion>默认陪伴</emotion>"
                    }
                }
            ]
        }
        mock_response.raise_for_status = MagicMock()

        with patch.object(
            service.client, "post", new_callable=AsyncMock
        ) as mock_post:
            mock_post.return_value = mock_response

            result = await service.chat(
                [{"role": "user", "content": "测试"}], stream=False
            )

            assert isinstance(result, LLMResponse)
            assert result.content == "测试"

        await service.close()

    @pytest.mark.asyncio
    async def test_close(self) -> None:
        """关闭服务."""
        config = LLMConfig(api_key="test_key")
        service = LLMService(config)

        with patch.object(
            service.client, "aclose", new_callable=AsyncMock
        ) as mock_close:
            await service.close()
            mock_close.assert_called_once()

    @pytest.mark.asyncio
    async def test_request_headers(self) -> None:
        """验证请求头."""
        config = LLMConfig(api_key="my_secret_key")
        service = LLMService(config)

        mock_response = MagicMock()
        mock_response.json.return_value = {
            "choices": [
                {
                    "message": {
                        "content": "<content>测试</content><emotion>默认陪伴</emotion>"
                    }
                }
            ]
        }
        mock_response.raise_for_status = MagicMock()

        with patch.object(
            service.client, "post", new_callable=AsyncMock
        ) as mock_post:
            mock_post.return_value = mock_response

            await service.chat_non_stream([{"role": "user", "content": "测试"}])

            call_args = mock_post.call_args
            headers = call_args[1]["headers"]
            assert headers["Content-Type"] == "application/json"
            assert headers["Authorization"] == "Bearer my_secret_key"

        await service.close()

    @pytest.mark.asyncio
    async def test_multiple_messages_context(self) -> None:
        """多轮对话上下文."""
        config = LLMConfig(api_key="test_key")
        service = LLMService(config)

        mock_response = MagicMock()
        mock_response.json.return_value = {
            "choices": [
                {
                    "message": {
                        "content": "<content>你是小明</content><emotion>默认陪伴</emotion>"
                    }
                }
            ]
        }
        mock_response.raise_for_status = MagicMock()

        messages = [
            {"role": "user", "content": "我叫小明"},
            {"role": "assistant", "content": "你好小明"},
            {"role": "user", "content": "你还记得我叫什么吗"},
        ]

        with patch.object(
            service.client, "post", new_callable=AsyncMock
        ) as mock_post:
            mock_post.return_value = mock_response

            await service.chat_non_stream(messages)

            call_args = mock_post.call_args
            sent_messages = call_args[1]["json"]["messages"]
            # system + 3 user/assistant messages
            assert len(sent_messages) == 4
            assert sent_messages[0]["role"] == "system"

        await service.close()
