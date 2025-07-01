#!/usr/bin/env python3
"""
简化的Gemini CLI服务 - 使用 -p 参数进行非交互式调用
无需复杂的进程池、PTY通信或ANSI码处理
"""

import asyncio
import json
import os
import re
from typing import AsyncGenerator, Optional


class SimplifiedGeminiCLI:
    """
    简化的Gemini CLI包装器
    
    使用 -p 参数直接调用，避免交互式界面的复杂性
    优势：
    - 无需PTY通信
    - 无需ANSI码处理
    - 无需复杂的模式匹配
    - 输出直接可用
    - 更稳定、更简单
    """
    
    def __init__(self, cli_path: str = "/usr/local/bin/gemini"):
        self.cli_path = cli_path
    
    async def execute_prompt(
        self, 
        prompt: str, 
        model: str = "gemini-2.5-pro",
        timeout: int = 60
    ) -> str:
        """
        执行单个提示并返回完整响应
        
        Args:
            prompt: 用户提示
            model: 模型名称
            timeout: 超时时间（秒）
            
        Returns:
            完整的响应文本
        """
        cmd = [
            self.cli_path,
            "-m", model,
            "-p", prompt
        ]
        
        try:
            process = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                env=os.environ.copy()
            )
            
            stdout, stderr = await asyncio.wait_for(
                process.communicate(), 
                timeout=timeout
            )
            
            if process.returncode != 0:
                error_msg = stderr.decode('utf-8', errors='ignore').strip()
                raise RuntimeError(f"Gemini CLI failed with code {process.returncode}: {error_msg}")
            
            response = stdout.decode('utf-8', errors='ignore').strip()
            return response
            
        except asyncio.TimeoutError:
            raise TimeoutError(f"Gemini CLI command timed out after {timeout} seconds")
        except Exception as e:
            raise RuntimeError(f"Failed to execute Gemini CLI: {e}")
    
    async def execute_prompt_stream(
        self, 
        prompt: str, 
        model: str = "gemini-2.5-pro",
        timeout: int = 60
    ) -> AsyncGenerator[str, None]:
        """
        执行提示并流式返回响应
        
        Args:
            prompt: 用户提示
            model: 模型名称
            timeout: 超时时间（秒）
            
        Yields:
            响应文本的片段
        """
        cmd = [
            self.cli_path,
            "-m", model,
            "-p", prompt
        ]
        
        try:
            process = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                env=os.environ.copy()
            )
            
            # 读取stdout流
            buffer = ""
            start_time = asyncio.get_event_loop().time()
            
            while True:
                current_time = asyncio.get_event_loop().time()
                if current_time - start_time > timeout:
                    process.kill()
                    raise TimeoutError(f"Gemini CLI command timed out after {timeout} seconds")
                
                try:
                    # 非阻塞读取
                    data = await asyncio.wait_for(
                        process.stdout.read(1024), 
                        timeout=0.1
                    )
                    
                    if not data:
                        # 进程结束
                        break
                    
                    chunk = data.decode('utf-8', errors='ignore')
                    buffer += chunk
                    
                    # 按行分割并yield
                    lines = buffer.split('\n')
                    buffer = lines[-1]  # 保留最后一行（可能不完整）
                    
                    for line in lines[:-1]:
                        if line.strip():
                            yield line.strip()
                    
                except asyncio.TimeoutError:
                    # 没有新数据，检查进程状态
                    if process.returncode is not None:
                        break
                    continue
            
            # 处理剩余的buffer
            if buffer.strip():
                yield buffer.strip()
            
            # 等待进程完成并检查错误
            await process.wait()
            
            if process.returncode != 0:
                stderr_data = await process.stderr.read()
                error_msg = stderr_data.decode('utf-8', errors='ignore').strip()
                raise RuntimeError(f"Gemini CLI failed with code {process.returncode}: {error_msg}")
                
        except asyncio.TimeoutError:
            if process:
                process.kill()
            raise TimeoutError(f"Gemini CLI command timed out after {timeout} seconds")
        except Exception as e:
            if process:
                process.kill()
            raise RuntimeError(f"Failed to execute Gemini CLI: {e}")
    
    def estimate_tokens(self, text: str) -> int:
        """
        估算文本的token数量（简单实现）
        """
        # 简单的token估算：大约4个字符 = 1个token
        return len(text) // 4
    
    async def get_model_info(self) -> dict:
        """
        获取模型信息（如果CLI支持）
        """
        try:
            cmd = [self.cli_path, "--help"]
            process = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            
            stdout, stderr = await process.communicate()
            
            # 从帮助信息中提取默认模型
            help_text = stdout.decode('utf-8', errors='ignore')
            model_match = re.search(r'default: "(.*?)"', help_text)
            default_model = model_match.group(1) if model_match else "gemini-2.5-pro"
            
            return {
                "default_model": default_model,
                "cli_path": self.cli_path,
                "available": True
            }
            
        except Exception as e:
            return {
                "default_model": "gemini-2.5-pro",
                "cli_path": self.cli_path,
                "available": False,
                "error": str(e)
            }


# 使用示例
async def demo():
    """演示简化版本的使用"""
    
    cli = SimplifiedGeminiCLI()
    
    print("🧪 测试简化版Gemini CLI")
    print("=" * 50)
    
    # 测试连接
    print("🔗 测试连接...")
    if await cli.test_connection():
        print("✅ 连接成功！")
    else:
        print("❌ 连接失败")
        return
    
    # 测试简单提示
    print("\n📝 测试简单数学问题...")
    response = await cli.execute_prompt("What is 5 + 3?")
    print(f"🤖 响应: '{response}'")
    
    # 测试复杂提示  
    print("\n📝 测试复杂提示...")
    response = await cli.execute_prompt("Explain quantum computing in one sentence.")
    print(f"🤖 响应: '{response}'")
    
    # 测试流式输出
    print("\n🌊 测试流式输出...")
    print("🤖 流式响应:")
    async for chunk in cli.execute_prompt_stream("Write a haiku about programming."):
        print(f"   📤 {chunk}", end='', flush=True)
    print("\n")

if __name__ == "__main__":
    asyncio.run(demo()) 