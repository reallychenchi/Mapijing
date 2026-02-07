# 实现计划 - 阶段 4：LLM 对话

> 版本：1.0
> 更新日期：2026-02-07

## 阶段目标

集成 DeepSeek API，实现 LLM 对话功能，包括情感解析和头像切换，以及对话上下文管理。

**前置条件：** 阶段 3（语音识别）已完成

---

## 1. 任务清单

| 序号 | 任务 | 类型 | 可单元测试 |
|------|------|------|-----------|
| 4.1 | 实现 LLM 服务（DeepSeek API 调用） | 后端 | ✓ |
| 4.2 | 实现情感解析器 | 后端 | ✓ |
| 4.3 | 实现对话上下文管理 | 后端 | ✓ |
| 4.4 | 实现对话服务（整合 ASR + LLM） | 后端 | ✓ |
| 4.5 | 前端情感状态联动头像切换 | 前端 | ✓ |
| 4.6 | 前端展示 LLM 回复文字 | 前端 | ✓ |

---

## 2. 详细任务说明

### 2.1 实现 LLM 服务

**文件：** `backend/services/llm_service.py`

**功能：**
- 调用 DeepSeek API（流式/非流式）
- 构建系统提示词
- 处理 API 响应

**系统提示词（来自需求）：**
```
你是一个善解人意的小马，帮助对方聊天。返回格式要求用 <content> </content> <emotion></emotion> 标签标记，content中间是返回的对话，emotion中间是当前小马的表情，有 默认陪伴、共情倾听、安慰支持、轻松愉悦 四种，其中 默认陪伴 是默认状态。
```

**接口定义：**
```python
from typing import AsyncGenerator, Optional
from dataclasses import dataclass
import httpx

@dataclass
class LLMResponse:
    """LLM 响应结构"""
    content: str          # 对话内容
    emotion: str          # 情感状态
    raw_response: str     # 原始响应（调试用）

@dataclass
class LLMConfig:
    """LLM 配置"""
    api_url: str = "https://api.deepseek.com/chat/completions"
    api_key: str = ""
    model: str = "deepseek-chat"
    max_tokens: int = 2048
    temperature: float = 0.7

class LLMService:
    """DeepSeek LLM 服务"""

    SYSTEM_PROMPT = """你是一个善解人意的小马，帮助对方聊天。返回格式要求用 <content> </content> <emotion></emotion> 标签标记，content中间是返回的对话，emotion中间是当前小马的表情，有 默认陪伴、共情倾听、安慰支持、轻松愉悦 四种，其中 默认陪伴 是默认状态。"""

    def __init__(self, config: LLMConfig):
        self.config = config
        self.client = httpx.AsyncClient(timeout=60.0)

    async def chat(
        self,
        messages: list[dict],
        stream: bool = False
    ) -> LLMResponse | AsyncGenerator[str, None]:
        """
        发送对话请求

        Args:
            messages: 对话历史 [{"role": "user", "content": "..."}]
            stream: 是否流式返回

        Returns:
            非流式: LLMResponse 对象
            流式: 异步生成器，逐字返回
        """
        pass

    async def chat_non_stream(self, messages: list[dict]) -> LLMResponse:
        """非流式对话（本阶段使用）"""
        pass

    async def chat_stream(self, messages: list[dict]) -> AsyncGenerator[str, None]:
        """流式对话（阶段5使用，预留接口）"""
        pass

    async def close(self):
        """关闭 HTTP 客户端"""
        await self.client.aclose()
```

**API 调用实现：**
```python
async def chat_non_stream(self, messages: list[dict]) -> LLMResponse:
    """非流式对话"""
    # 构建请求体
    full_messages = [
        {"role": "system", "content": self.SYSTEM_PROMPT},
        *messages
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

def _parse_response(self, raw: str) -> LLMResponse:
    """解析 LLM 响应，提取 content 和 emotion"""
    # 调用 EmotionParser 解析
    from .emotion_parser import EmotionParser
    parser = EmotionParser()
    return parser.parse(raw)
```

---

### 2.2 实现情感解析器

**文件：** `backend/services/emotion_parser.py`

**功能：**
- 解析 LLM 返回的 XML 格式
- 提取 `<content>` 和 `<emotion>` 标签内容
- 处理格式异常情况

**接口定义：**
```python
import re
from dataclasses import dataclass
from typing import Optional

@dataclass
class ParsedResponse:
    """解析后的响应"""
    content: str          # 对话内容
    emotion: str          # 情感状态（中文）
    is_valid: bool        # 解析是否成功

class EmotionParser:
    """情感解析器"""

    VALID_EMOTIONS = ["默认陪伴", "共情倾听", "安慰支持", "轻松愉悦"]
    DEFAULT_EMOTION = "默认陪伴"

    # 正则表达式
    CONTENT_PATTERN = re.compile(r"<content>(.*?)</content>", re.DOTALL)
    EMOTION_PATTERN = re.compile(r"<emotion>(.*?)</emotion>", re.DOTALL)

    def parse(self, raw_response: str) -> ParsedResponse:
        """
        解析 LLM 响应

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
            is_valid=bool(content)  # content 不为空即认为有效
        )

    def _extract_content(self, raw: str) -> str:
        """提取 content 标签内容"""
        match = self.CONTENT_PATTERN.search(raw)
        if match:
            return match.group(1).strip()

        # 兜底：如果没有标签，返回整个响应（去除可能的 emotion 标签）
        fallback = self.EMOTION_PATTERN.sub("", raw).strip()
        return fallback if fallback else raw.strip()

    def _extract_emotion(self, raw: str) -> str:
        """提取 emotion 标签内容"""
        match = self.EMOTION_PATTERN.search(raw)
        if match:
            emotion = match.group(1).strip()
            # 验证情感值是否有效
            if emotion in self.VALID_EMOTIONS:
                return emotion

        # 默认返回 "默认陪伴"
        return self.DEFAULT_EMOTION
```

**测试用例：**
```python
# 正常格式
input1 = "<content>我理解你的感受，能告诉我发生了什么吗？</content><emotion>共情倾听</emotion>"
# 期望: content="我理解你的感受，能告诉我发生了什么吗？", emotion="共情倾听"

# 缺少 emotion
input2 = "<content>你好啊！</content>"
# 期望: content="你好啊！", emotion="默认陪伴"

# 无效 emotion
input3 = "<content>哈哈</content><emotion>开心</emotion>"
# 期望: content="哈哈", emotion="默认陪伴"（无效值回退到默认）

# 完全无标签
input4 = "你好，我是小马"
# 期望: content="你好，我是小马", emotion="默认陪伴"
```

---

### 2.3 实现对话上下文管理

**文件：** `backend/services/context_manager.py`

**功能：**
- 维护对话历史
- 控制上下文长度（50k tokens 限制）
- 截断早期对话

**接口定义：**
```python
from dataclasses import dataclass, field
from typing import Optional

@dataclass
class Message:
    """对话消息"""
    role: str       # "user" | "assistant"
    content: str    # 消息内容

@dataclass
class ContextConfig:
    """上下文配置"""
    max_tokens: int = 50000           # 最大 token 数
    chars_per_token: float = 1.5      # 中文约 1.5 字符/token
    min_history_count: int = 2        # 至少保留的对话轮数

class ContextManager:
    """对话上下文管理器"""

    def __init__(self, config: Optional[ContextConfig] = None):
        self.config = config or ContextConfig()
        self.messages: list[Message] = []

    def add_user_message(self, content: str) -> None:
        """添加用户消息"""
        self.messages.append(Message(role="user", content=content))
        self._trim_if_needed()

    def add_assistant_message(self, content: str) -> None:
        """添加助手消息"""
        self.messages.append(Message(role="assistant", content=content))
        self._trim_if_needed()

    def get_messages(self) -> list[dict]:
        """获取消息列表（API 格式）"""
        return [{"role": m.role, "content": m.content} for m in self.messages]

    def clear(self) -> None:
        """清空上下文"""
        self.messages.clear()

    def estimate_tokens(self) -> int:
        """估算当前 token 数"""
        total_chars = sum(len(m.content) for m in self.messages)
        return int(total_chars / self.config.chars_per_token)

    def _trim_if_needed(self) -> None:
        """如果超过限制，截断早期消息"""
        while (self.estimate_tokens() > self.config.max_tokens
               and len(self.messages) > self.config.min_history_count * 2):
            # 删除最早的一轮对话（user + assistant）
            self.messages.pop(0)
            if self.messages and self.messages[0].role == "assistant":
                self.messages.pop(0)
```

**Token 估算说明：**
- 中文文本约 1.5 字符 = 1 token（经验值）
- 50k tokens ≈ 75k 中文字符
- 实际使用中可根据 DeepSeek 的 tokenizer 调整

---

### 2.4 实现对话服务（整合 ASR + LLM）

**文件：** `backend/services/conversation_service.py`

**功能：**
- 整合 ASR 识别结果和 LLM 对话
- 管理单个会话的完整流程
- 下发情感状态消息

**接口定义：**
```python
from dataclasses import dataclass
from typing import Callable, Awaitable

@dataclass
class ConversationConfig:
    """会话配置"""
    llm_config: 'LLMConfig'
    context_config: 'ContextConfig' = None

class ConversationService:
    """会话服务"""

    def __init__(self, config: ConversationConfig):
        self.config = config
        self.llm_service = LLMService(config.llm_config)
        self.context_manager = ContextManager(config.context_config)
        self.current_emotion = "默认陪伴"

    async def process_user_input(
        self,
        user_text: str,
        on_emotion_change: Callable[[str], Awaitable[None]] = None,
        on_llm_response: Callable[[str], Awaitable[None]] = None,
    ) -> str:
        """
        处理用户输入，返回 LLM 回复

        Args:
            user_text: 用户输入文字（ASR 识别结果）
            on_emotion_change: 情感变化回调
            on_llm_response: LLM 回复回调

        Returns:
            LLM 回复文字
        """
        # 1. 添加用户消息到上下文
        self.context_manager.add_user_message(user_text)

        # 2. 调用 LLM
        messages = self.context_manager.get_messages()
        response = await self.llm_service.chat_non_stream(messages)

        # 3. 处理情感变化
        if response.emotion != self.current_emotion:
            self.current_emotion = response.emotion
            if on_emotion_change:
                await on_emotion_change(response.emotion)

        # 4. 添加助手消息到上下文
        self.context_manager.add_assistant_message(response.content)

        # 5. 回调通知
        if on_llm_response:
            await on_llm_response(response.content)

        return response.content

    def get_current_emotion(self) -> str:
        """获取当前情感状态"""
        return self.current_emotion

    def reset(self) -> None:
        """重置会话"""
        self.context_manager.clear()
        self.current_emotion = "默认陪伴"

    async def close(self) -> None:
        """关闭服务"""
        await self.llm_service.close()
```

---

### 2.5 更新 WebSocket 处理器

**文件：** `backend/api/websocket.py`（更新）

**新增功能：**
- ASR 识别完成后调用 LLM
- 下发 emotion 消息
- 下发 LLM 回复文字

**更新代码：**
```python
from services.conversation_service import ConversationService, ConversationConfig
from services.llm_service import LLMConfig

class WebSocketHandler:
    def __init__(self, websocket: WebSocket):
        self.websocket = websocket
        self.conversation_service = None

    async def initialize(self):
        """初始化服务"""
        config = ConversationConfig(
            llm_config=LLMConfig(
                api_key=settings.DEEPSEEK_API_KEY,
            )
        )
        self.conversation_service = ConversationService(config)

    async def on_asr_complete(self, final_text: str):
        """ASR 识别完成回调"""
        # 发送 asr_end 消息
        await self.send_message({
            "type": "asr_end",
            "data": {"text": final_text}
        })

        # 调用 LLM 处理
        await self.conversation_service.process_user_input(
            user_text=final_text,
            on_emotion_change=self._on_emotion_change,
            on_llm_response=self._on_llm_response,
        )

    async def _on_emotion_change(self, emotion: str):
        """情感变化回调"""
        await self.send_message({
            "type": "emotion",
            "data": {"emotion": emotion}
        })

    async def _on_llm_response(self, content: str):
        """LLM 回复回调（本阶段仅发送文字）"""
        # 本阶段暂时直接发送完整文字
        # 阶段 5 将改为 tts_chunk 同步发送
        await self.send_message({
            "type": "llm_response",  # 临时消息类型，阶段5替换
            "data": {"text": content}
        })
```

---

### 2.6 前端情感状态联动头像切换

**文件：** `frontend/src/hooks/useConversation.ts`（更新）

**新增功能：**
- 监听 `emotion` 消息
- 更新头像状态

**更新代码：**
```typescript
import { useEmotion } from './useEmotion';

export const useConversation = () => {
  const { setEmotionFromServer } = useEmotion();
  const { onMessage } = useWebSocket();

  useEffect(() => {
    const unsubscribe = onMessage((message) => {
      switch (message.type) {
        case 'emotion':
          // 收到情感状态，更新头像
          setEmotionFromServer(message.data.emotion);
          break;

        case 'llm_response':
          // 收到 LLM 回复（本阶段临时处理）
          setText(message.data.text);
          setSpeaker('assistant');
          break;

        // ... 其他消息处理
      }
    });

    return unsubscribe;
  }, []);
};
```

---

### 2.7 前端展示 LLM 回复文字

**文件：** `frontend/src/components/TextArea/TextArea.tsx`（更新）

**说明：** 阶段 1 已实现文字展示功能，本阶段只需确保能正确展示 LLM 回复。

**验证要点：**
- 收到 `llm_response` 消息后更新文字
- speaker 切换为 `assistant`
- 文字正确渲染

---

## 3. 配置文件更新

**文件：** `backend/config/settings.py`

**新增配置：**
```python
from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    # 火山引擎配置（阶段3已有）
    VOLC_ASR_APP_ID: str = ""
    VOLC_ASR_TOKEN: str = ""

    # DeepSeek 配置（新增）
    DEEPSEEK_API_KEY: str = ""
    DEEPSEEK_API_URL: str = "https://api.deepseek.com/chat/completions"
    DEEPSEEK_MODEL: str = "deepseek-chat"
    DEEPSEEK_MAX_TOKENS: int = 2048
    DEEPSEEK_TEMPERATURE: float = 0.7

    # 上下文配置（新增）
    CONTEXT_MAX_TOKENS: int = 50000

    class Config:
        env_file = ".env"

settings = Settings()
```

**文件：** `backend/.env.example`（更新）

```
# 火山引擎 ASR
VOLC_ASR_APP_ID=your_app_id
VOLC_ASR_TOKEN=your_token

# DeepSeek LLM
DEEPSEEK_API_KEY=sk-903a962786f34773a1680f6fb6fad64d
DEEPSEEK_API_URL=https://api.deepseek.com/chat/completions
DEEPSEEK_MODEL=deepseek-chat
DEEPSEEK_MAX_TOKENS=2048
DEEPSEEK_TEMPERATURE=0.7

# 上下文管理
CONTEXT_MAX_TOKENS=50000
```

---

## 4. 测试计划

### 4.1 单元测试

| 测试对象 | 测试内容 | 文件 |
|----------|----------|------|
| EmotionParser | 各种格式解析 | `tests/test_emotion_parser.py` |
| ContextManager | 消息管理、截断逻辑 | `tests/test_context_manager.py` |
| LLMService | API 调用（Mock） | `tests/test_llm_service.py` |
| ConversationService | 完整流程（Mock） | `tests/test_conversation_service.py` |

**EmotionParser 测试用例：**
```python
import pytest
from services.emotion_parser import EmotionParser

class TestEmotionParser:
    def setup_method(self):
        self.parser = EmotionParser()

    def test_normal_format(self):
        """正常格式解析"""
        raw = "<content>我理解你的感受</content><emotion>共情倾听</emotion>"
        result = self.parser.parse(raw)
        assert result.content == "我理解你的感受"
        assert result.emotion == "共情倾听"
        assert result.is_valid == True

    def test_missing_emotion(self):
        """缺少 emotion 标签"""
        raw = "<content>你好</content>"
        result = self.parser.parse(raw)
        assert result.content == "你好"
        assert result.emotion == "默认陪伴"

    def test_invalid_emotion(self):
        """无效的情感值"""
        raw = "<content>哈哈</content><emotion>开心</emotion>"
        result = self.parser.parse(raw)
        assert result.emotion == "默认陪伴"

    def test_no_tags(self):
        """完全无标签"""
        raw = "你好，我是小马"
        result = self.parser.parse(raw)
        assert result.content == "你好，我是小马"
        assert result.emotion == "默认陪伴"

    def test_multiline_content(self):
        """多行内容"""
        raw = "<content>第一行\n第二行</content><emotion>安慰支持</emotion>"
        result = self.parser.parse(raw)
        assert "第一行" in result.content
        assert "第二行" in result.content
```

**ContextManager 测试用例：**
```python
import pytest
from services.context_manager import ContextManager, ContextConfig

class TestContextManager:
    def test_add_messages(self):
        """添加消息"""
        cm = ContextManager()
        cm.add_user_message("你好")
        cm.add_assistant_message("你好！很高兴见到你")

        messages = cm.get_messages()
        assert len(messages) == 2
        assert messages[0]["role"] == "user"
        assert messages[1]["role"] == "assistant"

    def test_trim_when_exceed(self):
        """超过限制时截断"""
        config = ContextConfig(max_tokens=100, chars_per_token=1)
        cm = ContextManager(config)

        # 添加超长内容
        for i in range(10):
            cm.add_user_message("x" * 50)
            cm.add_assistant_message("y" * 50)

        # 验证被截断
        assert cm.estimate_tokens() <= 100

    def test_clear(self):
        """清空上下文"""
        cm = ContextManager()
        cm.add_user_message("test")
        cm.clear()
        assert len(cm.get_messages()) == 0
```

**LLMService 测试用例（Mock）：**
```python
import pytest
from unittest.mock import AsyncMock, patch
from services.llm_service import LLMService, LLMConfig

class TestLLMService:
    @pytest.mark.asyncio
    async def test_chat_non_stream(self):
        """非流式对话"""
        config = LLMConfig(api_key="test_key")
        service = LLMService(config)

        # Mock HTTP 响应
        mock_response = {
            "choices": [{
                "message": {
                    "content": "<content>你好</content><emotion>默认陪伴</emotion>"
                }
            }]
        }

        with patch.object(service.client, 'post', new_callable=AsyncMock) as mock_post:
            mock_post.return_value.json.return_value = mock_response
            mock_post.return_value.raise_for_status = lambda: None

            result = await service.chat_non_stream([{"role": "user", "content": "你好"}])

            assert result.content == "你好"
            assert result.emotion == "默认陪伴"

        await service.close()
```

### 4.2 手工测试

| 测试项 | 验证内容 |
|--------|----------|
| 对话回复 | 说话后收到 LLM 回复文字 |
| 情感切换 | 不同对话内容触发不同情感，头像切换 |
| 多轮对话 | 连续对话，LLM 记住上下文 |
| 长对话截断 | 超长对话后，早期内容被截断 |
| 错误处理 | API 调用失败时显示错误 |

**手工测试脚本：**
```bash
# 1. 启动后端
cd backend
uvicorn main:app --reload

# 2. 启动前端
cd frontend
npm run dev

# 3. 打开浏览器，进行以下测试：

# 测试 1: 基本对话
# - 说 "你好"
# - 验证：收到回复文字，头像为默认状态

# 测试 2: 情感触发
# - 说 "我今天心情不太好"
# - 验证：头像切换为共情倾听或安慰支持

# 测试 3: 开心对话
# - 说 "哈哈，告诉你一个笑话"
# - 验证：头像可能切换为轻松愉悦

# 测试 4: 多轮上下文
# - 连续说 "我叫小明" → "你还记得我叫什么吗？"
# - 验证：LLM 回复中提到 "小明"
```

---

## 5. 交付物

完成本阶段后，应具备：

- [ ] `backend/services/llm_service.py` - LLM 服务实现
- [ ] `backend/services/emotion_parser.py` - 情感解析器实现
- [ ] `backend/services/context_manager.py` - 上下文管理器实现
- [ ] `backend/services/conversation_service.py` - 对话服务实现
- [ ] `backend/tests/test_emotion_parser.py` - 情感解析器单元测试
- [ ] `backend/tests/test_context_manager.py` - 上下文管理器单元测试
- [ ] `backend/tests/test_llm_service.py` - LLM 服务单元测试
- [ ] ASR 识别完成后自动调用 LLM
- [ ] 情感状态下发，前端头像切换
- [ ] LLM 回复文字展示
- [ ] 多轮对话上下文保持
- [ ] 单元测试全部通过

---

## 6. 预计产出文件

```
backend/
├── services/
│   ├── llm_service.py          # 新增
│   ├── emotion_parser.py       # 新增
│   ├── context_manager.py      # 新增
│   └── conversation_service.py # 新增/更新
├── config/
│   └── settings.py             # 更新
├── api/
│   └── websocket.py            # 更新
├── tests/
│   ├── test_emotion_parser.py  # 新增
│   ├── test_context_manager.py # 新增
│   └── test_llm_service.py     # 新增
└── .env.example                # 更新

frontend/
└── src/
    └── hooks/
        └── useConversation.ts  # 更新
```

---

## 7. 注意事项

### 7.1 API Key 安全
- DeepSeek API Key 存储在 `.env` 文件中
- `.env` 文件不提交到版本控制
- 前端不能直接访问 API Key

### 7.2 错误处理
- API 调用超时（60秒）
- API 返回非 200 状态码
- 响应格式解析失败（兜底处理）

### 7.3 流式支持预留
- 本阶段使用非流式调用（简化实现）
- LLMService 预留 `chat_stream` 接口
- 阶段 5 将切换为流式调用

### 7.4 临时消息类型
- 本阶段使用 `llm_response` 消息类型下发文字
- 阶段 5 将替换为 `tts_chunk` 实现文字音频同步
