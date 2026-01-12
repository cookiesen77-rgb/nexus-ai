"""
上下文管理模块测试
"""

import pytest
import asyncio


class TestTokenCounter:
    """Token计数器测试"""
    
    def test_count_english(self):
        """测试英文计数"""
        from src.context import TokenCounter
        
        counter = TokenCounter()
        text = "Hello, world!"
        tokens = counter.count(text)
        
        assert tokens > 0
        assert tokens < len(text)  # Token数应小于字符数
    
    def test_count_chinese(self):
        """测试中文计数"""
        from src.context import TokenCounter
        
        counter = TokenCounter()
        text = "你好，世界！"
        tokens = counter.count(text)
        
        assert tokens > 0
    
    def test_count_messages(self):
        """测试消息列表计数"""
        from src.context import TokenCounter
        
        counter = TokenCounter()
        messages = [
            {"role": "user", "content": "Hello"},
            {"role": "assistant", "content": "Hi there!"}
        ]
        
        tokens = counter.count_messages(messages)
        assert tokens > 0
    
    def test_truncate(self):
        """测试截断"""
        from src.context import TokenCounter
        
        counter = TokenCounter()
        text = "This is a long text that should be truncated. " * 100
        
        truncated = counter.truncate_to_fit(text, max_tokens=50)
        
        assert counter.count(truncated) <= 55  # 允许一些误差


class TestContextWindow:
    """上下文窗口测试"""
    
    def test_add_messages(self):
        """测试添加消息"""
        from src.context import ContextWindow
        
        window = ContextWindow(max_tokens=1000)
        
        window.add_user_message("Hello")
        window.add_assistant_message("Hi there!")
        
        assert len(window) == 2
        assert window.get_total_tokens() > 0
    
    def test_get_messages(self):
        """测试获取消息"""
        from src.context import ContextWindow
        
        window = ContextWindow()
        window.set_system_message("You are helpful.")
        window.add_user_message("Hello")
        
        messages = window.get_messages()
        
        assert len(messages) == 2
        assert messages[0]["role"] == "system"
        assert messages[1]["role"] == "user"
    
    def test_usage_ratio(self):
        """测试使用率"""
        from src.context import ContextWindow
        
        window = ContextWindow(max_tokens=100, reserve_tokens=20)
        
        # 空窗口使用率应该很低（可能有少量初始化token）
        assert window.get_usage_ratio() < 0.1
        
        window.add_user_message("Hello " * 10)
        
        assert window.get_usage_ratio() > 0
    
    def test_trim_to_fit(self):
        """测试裁剪"""
        from src.context import ContextWindow
        
        window = ContextWindow(max_tokens=200, reserve_tokens=50)
        
        # 添加多条消息
        for i in range(20):
            window.add_user_message(f"Message {i}")
        
        original_count = len(window)
        removed = window.trim_to_fit(target_tokens=50)
        
        assert removed > 0
        assert len(window) < original_count


class TestCompressor:
    """压缩器测试"""
    
    def test_rule_based_compress(self):
        """测试规则压缩"""
        from src.context import ContextCompressor, Message
        
        compressor = ContextCompressor()
        
        # 使用更长的消息确保压缩有效果
        messages = [
            Message(role="user", content="What is Python programming language and how does it work?"),
            Message(role="assistant", content="Python is a high-level, interpreted programming language known for its clear syntax and versatility. It supports multiple paradigms."),
            Message(role="user", content="How do I install Python on my computer? What are the steps?"),
            Message(role="assistant", content="You can download Python from the official website python.org. Choose the version for your operating system and follow the installer."),
        ]
        
        summary = compressor.compress_sync(messages)
        
        # 确保生成了摘要
        assert len(summary) > 0
    
    def test_compress_text(self):
        """测试文本压缩"""
        from src.context import compress_text
        
        text = "This is a long text. " * 100
        compressed = compress_text(text, max_tokens=50)
        
        assert len(compressed) < len(text)


class TestConversationTracker:
    """对话Token跟踪测试"""
    
    def test_track_usage(self):
        """测试使用跟踪"""
        from src.context import ConversationTokenTracker
        
        tracker = ConversationTokenTracker()
        
        tracker.track(input_tokens=100, output_tokens=50)
        tracker.track(input_tokens=80, output_tokens=40)
        
        usage = tracker.get_session_usage()
        
        assert usage.input_tokens == 180
        assert usage.output_tokens == 90
        assert usage.total_tokens == 270
    
    def test_session_cost(self):
        """测试会话成本"""
        from src.context import ConversationTokenTracker
        
        tracker = ConversationTokenTracker()
        tracker.track(input_tokens=1000, output_tokens=500)
        
        cost = tracker.get_session_cost()
        assert cost > 0

