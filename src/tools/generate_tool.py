"""
内容生成工具

支持多媒体内容生成（图像、音频等）
"""

import os
import base64
from typing import Optional, Dict, Any
from dataclasses import dataclass
from datetime import datetime

from .base import BaseTool, ToolResult, ToolStatus


class GenerateTool(BaseTool):
    """
    内容生成工具
    
    支持生成图像、音频、文档等多媒体内容
    """
    
    name = "generate"
    description = "Generate multimedia content including images, audio, and documents"
    parameters = {
        "type": "object",
        "properties": {
            "type": {
                "type": "string",
                "enum": ["image", "audio", "document", "diagram"],
                "description": "Type of content to generate"
            },
            "prompt": {
                "type": "string",
                "description": "Generation prompt/description"
            },
            "format": {
                "type": "string",
                "description": "Output format (e.g., 'png', 'mp3', 'pdf')"
            },
            "output_path": {
                "type": "string",
                "description": "Path to save the generated content"
            },
            "options": {
                "type": "object",
                "description": "Additional generation options"
            }
        },
        "required": ["type", "prompt"]
    }
    
    async def execute(
        self,
        type: str,
        prompt: str,
        format: str = "",
        output_path: str = "",
        options: Dict[str, Any] = None
    ) -> ToolResult:
        """执行内容生成"""
        options = options or {}
        
        try:
            if type == "image":
                return await self._generate_image(prompt, format, output_path, options)
            elif type == "audio":
                return await self._generate_audio(prompt, format, output_path, options)
            elif type == "document":
                return await self._generate_document(prompt, format, output_path, options)
            elif type == "diagram":
                return await self._generate_diagram(prompt, format, output_path, options)
            else:
                return ToolResult(
                    status=ToolStatus.ERROR,
                    output="",
                    error=f"Unknown generation type: {type}"
                )
                
        except Exception as e:
            return ToolResult(
                status=ToolStatus.ERROR,
                output="",
                error=str(e)
            )
    
    async def _generate_image(
        self,
        prompt: str,
        format: str,
        output_path: str,
        options: Dict[str, Any]
    ) -> ToolResult:
        """生成图像"""
        # 这里应集成图像生成API (如OpenAI DALL-E, Stability AI等)
        # 目前返回占位结果
        
        try:
            # 尝试使用OpenAI DALL-E
            import openai
            
            client = openai.AsyncOpenAI()
            
            response = await client.images.generate(
                model="dall-e-3",
                prompt=prompt,
                size=options.get('size', '1024x1024'),
                quality=options.get('quality', 'standard'),
                n=1
            )
            
            image_url = response.data[0].url
            
            # 如果指定了输出路径，下载图像
            if output_path:
                import httpx
                async with httpx.AsyncClient() as client:
                    img_response = await client.get(image_url)
                    with open(output_path, 'wb') as f:
                        f.write(img_response.content)
                return ToolResult(
                    status=ToolStatus.SUCCESS,
                    output=f"Image saved to {output_path}",
                    data={'path': output_path, 'url': image_url}
                )
            
            return ToolResult(
                status=ToolStatus.SUCCESS,
                output=f"Image generated",
                data={'url': image_url}
            )
            
        except ImportError:
            return ToolResult(
                status=ToolStatus.ERROR,
                output="",
                error="OpenAI library not installed. Run: pip install openai"
            )
        except Exception as e:
            return ToolResult(
                status=ToolStatus.ERROR,
                output="",
                error=f"Image generation failed: {str(e)}"
            )
    
    async def _generate_audio(
        self,
        prompt: str,
        format: str,
        output_path: str,
        options: Dict[str, Any]
    ) -> ToolResult:
        """生成音频（语音合成）"""
        try:
            import openai
            
            client = openai.AsyncOpenAI()
            
            response = await client.audio.speech.create(
                model="tts-1",
                voice=options.get('voice', 'alloy'),
                input=prompt
            )
            
            output_path = output_path or f"speech_{datetime.now().strftime('%Y%m%d_%H%M%S')}.mp3"
            
            with open(output_path, 'wb') as f:
                f.write(response.content)
            
            return ToolResult(
                status=ToolStatus.SUCCESS,
                output=f"Audio saved to {output_path}",
                data={'path': output_path}
            )
            
        except ImportError:
            return ToolResult(
                status=ToolStatus.ERROR,
                output="",
                error="OpenAI library not installed"
            )
        except Exception as e:
            return ToolResult(
                status=ToolStatus.ERROR,
                output="",
                error=f"Audio generation failed: {str(e)}"
            )
    
    async def _generate_document(
        self,
        prompt: str,
        format: str,
        output_path: str,
        options: Dict[str, Any]
    ) -> ToolResult:
        """生成文档"""
        format = format or 'md'
        output_path = output_path or f"document_{datetime.now().strftime('%Y%m%d_%H%M%S')}.{format}"
        
        # 使用LLM生成文档内容
        try:
            from src.llm import create_allapi_client
            
            client = create_allapi_client()
            
            messages = [
                {"role": "system", "content": "You are a document writer. Generate well-structured content."},
                {"role": "user", "content": f"Generate a document about: {prompt}"}
            ]
            
            response = await client.complete(messages=messages)
            content = response.content
            
            # 如果需要PDF格式
            if format == 'pdf':
                # 需要安装markdown和weasyprint
                try:
                    import markdown
                    from weasyprint import HTML
                    
                    html = markdown.markdown(content)
                    HTML(string=html).write_pdf(output_path)
                except ImportError:
                    # 回退到markdown
                    output_path = output_path.replace('.pdf', '.md')
                    with open(output_path, 'w') as f:
                        f.write(content)
            else:
                with open(output_path, 'w') as f:
                    f.write(content)
            
            return ToolResult(
                status=ToolStatus.SUCCESS,
                output=f"Document saved to {output_path}",
                data={'path': output_path, 'content_preview': content[:500]}
            )
            
        except Exception as e:
            return ToolResult(
                status=ToolStatus.ERROR,
                output="",
                error=f"Document generation failed: {str(e)}"
            )
    
    async def _generate_diagram(
        self,
        prompt: str,
        format: str,
        output_path: str,
        options: Dict[str, Any]
    ) -> ToolResult:
        """生成图表"""
        diagram_type = options.get('diagram_type', 'mermaid')
        format = format or 'png'
        output_path = output_path or f"diagram_{datetime.now().strftime('%Y%m%d_%H%M%S')}.{format}"
        
        try:
            # 使用LLM生成图表代码
            from src.llm import create_allapi_client
            
            client = create_allapi_client()
            
            messages = [
                {"role": "system", "content": f"You are a diagram generator. Output only {diagram_type} diagram code, no explanation."},
                {"role": "user", "content": f"Generate a {diagram_type} diagram for: {prompt}"}
            ]
            
            response = await client.complete(messages=messages)
            diagram_code = response.content
            
            # 提取代码块
            if '```' in diagram_code:
                lines = diagram_code.split('```')
                if len(lines) >= 2:
                    diagram_code = lines[1]
                    if diagram_code.startswith('mermaid'):
                        diagram_code = diagram_code[7:]
            
            # 保存图表代码
            code_path = output_path.replace(f'.{format}', '.mmd')
            with open(code_path, 'w') as f:
                f.write(diagram_code.strip())
            
            # 尝试渲染 (需要安装mermaid-cli)
            try:
                import subprocess
                subprocess.run(
                    ['mmdc', '-i', code_path, '-o', output_path],
                    check=True,
                    capture_output=True
                )
                return ToolResult(
                    status=ToolStatus.SUCCESS,
                    output=f"Diagram saved to {output_path}",
                    data={'path': output_path, 'code_path': code_path}
                )
            except (FileNotFoundError, subprocess.CalledProcessError):
                return ToolResult(
                    status=ToolStatus.SUCCESS,
                    output=f"Diagram code saved to {code_path} (render tool not available)",
                    data={'code_path': code_path, 'code': diagram_code.strip()}
                )
                
        except Exception as e:
            return ToolResult(
                status=ToolStatus.ERROR,
                output="",
                error=f"Diagram generation failed: {str(e)}"
            )


# 工具实例
generate_tool = GenerateTool()

