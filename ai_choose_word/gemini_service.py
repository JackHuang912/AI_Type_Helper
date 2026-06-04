import os
import json
from google import genai
from google.genai import types
from pydantic import BaseModel, Field
client = genai.Client(api_key="輸入使用者gemini api")
class TyperResponse(BaseModel):
    converted_text: str = Field(description="將注音符號完美轉換後的繁體中文句子，不包含任何解釋、標點符號或問候語。")
def get_gemini_fallback(bpmf_str: str, context_str: str = "開始") -> str:#使用gemini進行注音長句語意推理
    try:
        prompt = f"""
        你是一個高智慧的繁體中文輸入法核心。
        目前使用者在英文輸入法下盲打了一串注音符號。
        
        【目前記憶的前文】：{context_str}
        【使用者輸入的注音符號】：{bpmf_str}
        
        請結合前文，將這串注音還原成最自然、最符合台灣習慣的繁體中文句子。
        """
        # 採用 gemini-2.5-flash 模型
        response = client.models.generate_content(
            model='gemini-2.5-flash',
            contents=prompt,
            config=types.GenerateContentConfig(
                response_mime_type="application/json",
                response_schema=TyperResponse,
                temperature=0.2
            )
        )
        response_data = json.loads(response.text)
        return response_data.get("converted_text", "")
        
    except Exception as e:
        error_msg = str(e)   
        if "429" in error_msg or "RESOURCE_EXHAUSTED" in error_msg:
            print("\n Gemini額度耗盡！切換為本地端模型。")
        return ""

# # 獨立測試用
# if __name__ == "__main__":
#     print("Connecting to Gemini API using new google-genai SDK...")
#     # 測試模擬：ㄉㄧˋㄦˋㄐㄧㄝ階ㄉㄨㄢˋ
#     test_result = get_gemini_fallback("ㄉㄧˋㄦˋㄐㄧㄝㄉㄨㄢˋ", "進行")
#     print(f"Test Result: {test_result}")