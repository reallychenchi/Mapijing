"""error_handler 模块测试."""


from utils.error_handler import (
    AppError,
    ErrorCode,
    create_error_from_exception,
    create_error_message,
)


class TestErrorCode:
    """ErrorCode 枚举测试."""

    def test_error_codes_exist(self) -> None:
        """测试错误码枚举值存在."""
        assert ErrorCode.ASR_ERROR.value == "ASR_ERROR"
        assert ErrorCode.LLM_ERROR.value == "LLM_ERROR"
        assert ErrorCode.TTS_ERROR.value == "TTS_ERROR"
        assert ErrorCode.NETWORK_ERROR.value == "NETWORK_ERROR"
        assert ErrorCode.UNKNOWN_ERROR.value == "UNKNOWN_ERROR"


class TestAppError:
    """AppError 数据类测试."""

    def test_create_app_error(self) -> None:
        """测试创建 AppError."""
        error = AppError(
            code=ErrorCode.ASR_ERROR,
            message="语音识别错误",
            details="详细信息",
        )
        assert error.code == ErrorCode.ASR_ERROR
        assert error.message == "语音识别错误"
        assert error.details == "详细信息"

    def test_create_app_error_without_details(self) -> None:
        """测试创建没有详情的 AppError."""
        error = AppError(
            code=ErrorCode.LLM_ERROR,
            message="对话错误",
        )
        assert error.code == ErrorCode.LLM_ERROR
        assert error.message == "对话错误"
        assert error.details is None


class TestCreateErrorMessage:
    """create_error_message 函数测试."""

    def test_create_error_message(self) -> None:
        """测试创建错误消息."""
        error = AppError(
            code=ErrorCode.TTS_ERROR,
            message="语音合成错误",
        )
        message = create_error_message(error)

        assert message["type"] == "error"
        assert message["data"]["code"] == "TTS_ERROR"
        assert message["data"]["message"] == "语音合成错误"


class TestCreateErrorFromException:
    """create_error_from_exception 函数测试."""

    def test_create_error_from_exception(self) -> None:
        """测试从异常创建 AppError."""
        exception = ValueError("测试异常")
        error = create_error_from_exception(
            exception=exception,
            error_code=ErrorCode.UNKNOWN_ERROR,
            default_message="发生错误",
        )

        assert error.code == ErrorCode.UNKNOWN_ERROR
        assert error.message == "发生错误"
        assert error.details == "测试异常"

    def test_create_error_from_exception_with_complex_message(self) -> None:
        """测试从复杂异常创建 AppError."""
        exception = RuntimeError("复杂错误: 包含详细信息")
        error = create_error_from_exception(
            exception=exception,
            error_code=ErrorCode.NETWORK_ERROR,
            default_message="网络错误",
        )

        assert error.code == ErrorCode.NETWORK_ERROR
        assert error.message == "网络错误"
        assert "复杂错误" in error.details  # type: ignore[operator]
