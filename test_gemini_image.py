#!/usr/bin/env python3
"""测试 Gemini 图片生成 API"""

import requests
import base64
import json
import os
from pathlib import Path

# API 配置
API_URL = "https://nexusapi.cn/v1beta/models/gemini-2.5-flash-image:generateContent"
API_KEY = os.getenv("ALLAPI_KEY", "")

def test_gemini_image_generation():
    """测试 Gemini 图片生成"""

    if not API_KEY:
        raise RuntimeError("Missing ALLAPI_KEY. Please export ALLAPI_KEY before running this test.")
    
    headers = {
        "x-goog-api-key": API_KEY,
        "Content-Type": "application/json"
    }
    
    payload = {
        "contents": [{
            "parts": [
                {"text": "Create a professional presentation slide background image. Modern tech style with blue gradient and subtle geometric patterns. No text, clean design, 16:9 aspect ratio."}
            ]
        }],
        "generationConfig": {
            "responseModalities": ["TEXT", "IMAGE"]
        }
    }
    
    print("正在调用 Gemini API 生成图片...")
    print(f"API URL: {API_URL}")
    
    try:
        response = requests.post(API_URL, headers=headers, json=payload, timeout=120)
        response.raise_for_status()
        
        result = response.json()
        print(f"\n响应状态码: {response.status_code}")
        
        # 解析响应
        if "candidates" in result and len(result["candidates"]) > 0:
            candidate = result["candidates"][0]
            content = candidate.get("content", {})
            parts = content.get("parts", [])
            
            text_response = None
            image_data = None
            
            for part in parts:
                if "text" in part:
                    text_response = part["text"]
                    print(f"\n文本响应: {text_response}")
                elif "inlineData" in part:
                    inline_data = part["inlineData"]
                    mime_type = inline_data.get("mimeType", "")
                    image_data = inline_data.get("data", "")
                    print(f"\n图片类型: {mime_type}")
                    print(f"图片数据大小: {len(image_data)} 字符 (base64)")
            
            # 保存图片
            if image_data:
                output_path = Path("/Users/mac/Desktop/manus/test_generated_image.png")
                image_bytes = base64.b64decode(image_data)
                output_path.write_bytes(image_bytes)
                print(f"\n图片已保存到: {output_path}")
                print(f"图片文件大小: {output_path.stat().st_size / 1024:.2f} KB")
                return True
            else:
                print("\n警告: 响应中没有图片数据")
                return False
        else:
            print(f"\n错误: 响应格式异常")
            print(json.dumps(result, indent=2, ensure_ascii=False)[:1000])
            return False
            
    except requests.exceptions.RequestException as e:
        print(f"\nAPI 调用失败: {e}")
        return False
    except Exception as e:
        print(f"\n处理响应时出错: {e}")
        return False

if __name__ == "__main__":
    success = test_gemini_image_generation()
    print(f"\n测试结果: {'成功' if success else '失败'}")

