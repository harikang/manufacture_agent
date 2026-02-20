"""
Backend Agent for Diecasting AI
FastAPI server with Bedrock Claude Tool Use for Lambda orchestration
Claude directly decides which tools to call and synthesizes the final response
"""
from fastapi import FastAPI, HTTPException
from fastapi.responses import StreamingResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import httpx
import json
import os
from typing import Dict, Any, Optional, List
import asyncio
import boto3
from botocore.auth import SigV4Auth
from botocore.awsrequest import AWSRequest
from botocore.credentials import Credentials
import requests

app = FastAPI(title="Diecasting AI Backend Agent")

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Lambda URLs (환경변수로 설정 필요)
USE_MOCK = os.getenv("USE_MOCK", "false").lower() == "true"
LAMBDA_T0_URL = os.getenv("LAMBDA_T0_URL", "https://your-lambda-t0-url.lambda-url.us-east-1.on.aws/")
LAMBDA_T1_URL = os.getenv("LAMBDA_T1_URL", "https://your-lambda-t1-url.lambda-url.us-east-1.on.aws/")
LAMBDA_T2_URL = os.getenv("LAMBDA_T2_URL", "https://your-lambda-t2-url.lambda-url.us-east-1.on.aws/")
LAMBDA_T3_URL = os.getenv("LAMBDA_T3_URL", "https://your-lambda-t3-url.lambda-url.us-east-1.on.aws/")

# Bedrock Client
bedrock_runtime = boto3.client('bedrock-runtime', region_name='us-east-1')
MODEL_ID = os.getenv("MODEL_ID", "us.anthropic.claude-sonnet-4-5-20250929-v1:0")

# AWS Session for SigV4 signing
session = boto3.Session(region_name='us-east-1')
credentials = session.get_credentials()

# In-Memory Conversation Storage
conversation_memory: Dict[str, List[Dict[str, Any]]] = {}
MAX_HISTORY_LENGTH = 10  # 최근 10개 메시지만 유지

def sign_request(url: str, method: str, payload: dict) -> dict:
    """Sign request with SigV4 for Lambda Function URL"""
    body = json.dumps(payload)
    request = AWSRequest(method=method, url=url, data=body, headers={
        'Content-Type': 'application/json'
    })
    SigV4Auth(credentials, 'lambda', 'us-east-1').add_auth(request)
    return dict(request.headers)

# Request Models
class PredictRequest(BaseModel):
    question: str
    features: Dict[str, float]
    session_id: Optional[str] = "default"

class SessionRequest(BaseModel):
    user_id: Optional[str] = "anonymous"

class KBIngestRequest(BaseModel):
    action: str
    job_id: Optional[str] = None

# =============================================================================
# Tool Definitions for Bedrock Claude
# =============================================================================
TOOLS = [
    {
        "name": "predict_quality",
        "description": """품질 예측 도구. 현재 공정 파라미터를 기반으로 제품이 양품/불량인지 예측합니다.
사용 시점:
- 사용자가 현재 조건에서 품질을 예측해달라고 할 때
- 불량 가능성, 양품 확률을 물어볼 때
- "예측해줘", "불량일까?", "품질 판정" 등의 질문""",
        "inputSchema": {
            "json": {
                "type": "object",
                "properties": {
                    "features": {
                        "type": "object",
                        "description": "공정 파라미터 딕셔너리 (센서값들)"
                    }
                },
                "required": ["features"]
            }
        }
    },
    {
        "name": "analyze_feature_importance",
        "description": """Feature Importance 분석 도구. 품질에 영향을 미치는 주요 변수를 분석합니다.
사용 시점:
- 어떤 변수가 품질에 영향을 미치는지 물어볼 때
- 불량 원인을 분석해달라고 할 때
- "왜 불량이야?", "영향 요인", "중요 변수" 등의 질문
주의: 이 도구를 사용하기 전에 반드시 predict_quality를 먼저 호출해야 합니다.""",
        "inputSchema": {
            "json": {
                "type": "object",
                "properties": {
                    "features": {
                        "type": "object",
                        "description": "공정 파라미터 딕셔너리"
                    },
                    "latent_features": {
                        "type": "array",
                        "items": {"type": "number"},
                        "description": "predict_quality에서 반환된 latent_features"
                    }
                },
                "required": ["features", "latent_features"]
            }
        }
    },
    {
        "name": "search_knowledge_base",
        "description": """공정 지식 검색 도구. Knowledge Base에서 관련 문서를 검색합니다.
사용 시점:
- 장비 스펙, 권장 범위를 물어볼 때
- SOP, 매뉴얼 내용을 찾을 때
- 트러블슈팅 가이드가 필요할 때
- "권장 범위", "스펙", "어떻게 해결", "방법" 등의 질문""",
        "inputSchema": {
            "json": {
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "검색할 질문 또는 키워드"
                    }
                },
                "required": ["query"]
            }
        }
    }
]

SYSTEM_PROMPT = """당신은 다이캐스팅 제조 공정 AI 어시스턴트입니다.
사용자의 질문을 분석하고, 적절한 도구를 호출하여 답변을 생성하세요.

## 도구 사용 가이드

1. **품질 예측 질문** → predict_quality 호출
   - "불량 가능성은?", "품질 예측해줘"

2. **원인 분석 질문** → predict_quality 먼저 호출 → 결과 확인 후 → analyze_feature_importance 호출
   - "왜 불량이야?", "어떤 변수가 영향을 미쳐?"
   - **중요: 반드시 predict_quality를 먼저 호출하고, 그 결과의 latent_features를 받은 후에 analyze_feature_importance를 호출하세요**
   - **두 도구를 동시에 호출하지 마세요. 순차적으로 호출해야 합니다.**

3. **공정 지식 질문** → search_knowledge_base 호출
   - "권장 범위", "스펙", "해결 방법"

## 중요 규칙
- **각 도구는 한 번만 호출하세요. 같은 도구를 여러 번 호출하지 마세요.**
- **search_knowledge_base 도구를 호출하고 결과를 받으면, 즉시 답변을 종료하세요. 절대 추가 도구를 호출하지 마세요.**
- analyze_feature_importance는 반드시 predict_quality 호출 후에만 사용하세요
- predict_quality의 응답에서 latent_features 배열을 추출하여 analyze_feature_importance에 전달해야 합니다
- 한 번에 하나의 도구만 호출하세요 (병렬 호출 금지)

## 응답 가이드
- **search_knowledge_base 결과를 받으면:**
  - answer 필드의 내용을 그대로 사용자에게 전달하세요
  - 절대 "관련 문서를 찾을 수 없습니다" 같은 말을 하지 마세요
  - answer 필드에 이미 완전한 답변이 들어있습니다
  - 다른 도구를 추가로 호출하지 마세요
- 예측 결과는 probability_percent 필드를 사용하여 %로 표시하세요 (예: "불량 확률 75.0%")
- Feature Importance는 top_features_percent 필드를 사용하여 %로 표시하세요 (예: "Temperature1: 15.23%")
- 상위 5개 변수를 강조하세요
- 한국어로 답변하세요"""

# =============================================================================
# Tool Result Summarizer (LLM에 전달할 때 토큰 절약)
# =============================================================================
def summarize_tool_result(tool_name: str, result: Dict[str, Any]) -> Dict[str, Any]:
    """도구 결과를 요약하여 LLM에 전달 (불필요한 데이터 제거)"""
    if tool_name == "predict_quality":
        # latent_features는 상위 24개만 전달``
        latent = result.get("latent_features", [])[:24]
        return {
            "prediction": result.get("prediction"),
            "latent_features": latent
        }
    elif tool_name == "analyze_feature_importance":
        # 상위 10개 feature만 전달, equipment_descriptions 제거
        top_features = result.get("top_features", [])[:10]
        return {
            "top_features": top_features,
            "top_features_percent": result.get("top_features_percent", [])[:10]
        }
    elif tool_name == "search_knowledge_base":
        # 상위 3개 결과만 전달
        results = result.get("results", [])[:3]
        return {"results": results}
    
    return result

# =============================================================================
# Lambda Callers (동기 버전 - Tool Use에서 사용) - SigV4 서명 적용
# =============================================================================
def call_lambda_t1_sync(features: Dict[str, float]) -> Dict[str, Any]:
    """품질 예측 Lambda 호출 (IAM 인증)"""
    if USE_MOCK:
        import random
        defect_prob = 0.75 if random.random() > 0.5 else 0.25
        return {
            "prediction": {
                "class": "defect" if defect_prob > 0.5 else "normal",
                "probability": defect_prob,
                "class_probabilities": {"normal": 1-defect_prob, "defect": defect_prob}
            },
            "latent_features": [random.random()*2-1 for _ in range(12)]
        }
    
    try:
        payload = {"features": features}
        headers = sign_request(LAMBDA_T1_URL, 'POST', payload)
        response = requests.post(
            LAMBDA_T1_URL,
            json=payload,
            headers=headers,
            timeout=30
        )
        data = response.json()
        body = data.get("body", data)
        if isinstance(body, str):
            body = json.loads(body)
        return body
    except Exception as e:
        return {"error": str(e)}

def call_lambda_t2_sync(features: Dict[str, float], latent: List[float]) -> Dict[str, Any]:
    """Feature Importance Lambda 호출 (IAM 인증)"""
    if USE_MOCK:
        import random
        feature_names = list(features.keys())
        random.shuffle(feature_names)
        return {
            "top_features": [[name, 0.15 - i*0.012] for i, name in enumerate(feature_names[:10])]
        }
    
    try:
        payload = {"features": features, "latent_features": latent, "top_n": 10}
        headers = sign_request(LAMBDA_T2_URL, 'POST', payload)
        response = requests.post(
            LAMBDA_T2_URL,
            json=payload,
            headers=headers,
            timeout=30
        )
        data = response.json()
        body = data.get("body", data)
        if isinstance(body, str):
            body = json.loads(body)
        return body
    except Exception as e:
        return {"error": str(e)}

def call_lambda_t3_sync(query: str) -> Dict[str, Any]:
    """Knowledge Base 검색 Lambda 호출 (IAM 인증)"""
    if USE_MOCK:
        return {
            "answer": f"'{query}'에 대한 답변입니다.\n\n다이캐스팅 공정에서 해당 파라미터의 권장 범위와 관리 방법에 대해 설명드립니다.",
            "sources": [{"title": "다이캐스팅 공정 가이드", "type": "Knowledge Base"}]
        }
    
    try:
        payload = {"query": query}
        headers = sign_request(LAMBDA_T3_URL, 'POST', payload)
        response = requests.post(
            LAMBDA_T3_URL,
            json=payload,
            headers=headers,
            timeout=30
        )
        print(f"🔍 Lambda T3 Response Status: {response.status_code}")
        print(f"🔍 Lambda T3 Raw Response: {response.text[:500]}")
        
        data = response.json()
        body = data.get("body", data)
        if isinstance(body, str):
            body = json.loads(body)
        
        print(f"🔍 Lambda T3 Parsed Body: {json.dumps(body, ensure_ascii=False)[:500]}")
        return body
    except Exception as e:
        print(f"❌ Lambda T3 Error: {str(e)}")
        import traceback
        traceback.print_exc()
        return {"error": str(e)}

# =============================================================================
# Tool Execution
# =============================================================================
def execute_tool(tool_name: str, tool_input: Dict[str, Any], features: Dict[str, float]) -> Dict[str, Any]:
    """도구 실행"""
    if tool_name == "predict_quality":
        # features는 tool_input에서 가져오거나, 요청의 features 사용
        feat = tool_input.get("features", features)
        result = call_lambda_t1_sync(feat)
        
        # 확률을 %로 변환 (NaN 방지)
        if "prediction" in result:
            pred = result["prediction"]
            if "probability" in pred and isinstance(pred["probability"], (int, float)):
                pred["probability_percent"] = f"{pred['probability'] * 100:.1f}%"
            else:
                pred["probability_percent"] = "0.0%"
            
            if "class_probabilities" in pred and isinstance(pred["class_probabilities"], dict):
                pred["class_probabilities_percent"] = {
                    k: f"{v * 100:.1f}%" if isinstance(v, (int, float)) else "0.0%"
                    for k, v in pred["class_probabilities"].items()
                }
        return result
    
    elif tool_name == "analyze_feature_importance":
        feat = tool_input.get("features", features)
        latent = tool_input.get("latent_features", [])
        result = call_lambda_t2_sync(feat, latent)
        
        # Feature Importance를 %로 변환 (NaN 방지)
        if "top_features" in result and isinstance(result["top_features"], list):
            result["top_features_percent"] = [
                [name, f"{importance * 100:.2f}%" if isinstance(importance, (int, float)) else "0.00%"]
                for name, importance in result["top_features"]
            ]
        return result
    
    elif tool_name == "search_knowledge_base":
        query = tool_input.get("query", "")
        return call_lambda_t3_sync(query)
    
    return {"error": f"Unknown tool: {tool_name}"}

# =============================================================================
# Bedrock Converse API with Tool Use
# =============================================================================

def run_agent_loop(question: str, features: Dict[str, float], session_id: str = "default"):
    """
    Bedrock Claude Tool Use 기반 에이전트 루프
    Claude가 도구 호출을 결정하고, 결과를 받아 최종 응답 생성
    """
    # 세션 메모리 초기화
    if session_id not in conversation_memory:
        conversation_memory[session_id] = []
    
    # 이전 대화 기록 가져오기
    history = conversation_memory[session_id]
    
    # 새 사용자 메시지 추가
    messages = []
    
    # 이전 대화 기록 추가 (최근 MAX_HISTORY_LENGTH개만)
    for msg in history[-MAX_HISTORY_LENGTH:]:
        messages.append(msg)
    
    # 현재 질문 추가
    current_message = {
        "role": "user",
        "content": [
            {
                "text": f"""사용자 질문: {question}

현재 공정 파라미터:
{json.dumps(features, indent=2, ensure_ascii=False)}

위 질문에 답변하기 위해 필요한 도구를 호출하세요."""
            }
        ]
    }
    messages.append(current_message)
    
    tool_results = []  # 도구 호출 결과 저장
    
    # Agent Loop - 최대 5회 반복
    for iteration in range(5):
        # Bedrock Converse API 호출
        response = bedrock_runtime.converse(
            modelId=MODEL_ID,
            system=[{"text": SYSTEM_PROMPT}],
            messages=messages,
            toolConfig={
                "tools": [
                    {"toolSpec": tool} for tool in TOOLS
                ]
            }
        )
        
        output = response.get("output", {})
        message = output.get("message", {})
        stop_reason = response.get("stopReason", "")
        
        # 응답 메시지를 대화에 추가
        messages.append(message)
        
        # 종료 조건: end_turn이면 최종 응답
        if stop_reason == "end_turn":
            # 텍스트 응답 추출
            final_text = ""
            for content in message.get("content", []):
                if "text" in content:
                    final_text = content["text"]
                    break
            
            return {
                "answer": final_text,
                "tool_results": tool_results
            }
        
        # Tool Use 처리
        if stop_reason == "tool_use":
            tool_use_results = []
            should_return_immediately = False
            immediate_return_data = None
            
            for content in message.get("content", []):
                if "toolUse" in content:
                    tool_use = content["toolUse"]
                    tool_name = tool_use["name"]
                    tool_input = tool_use.get("input", {})
                    tool_use_id = tool_use["toolUseId"]
                    
                    # 도구 실행
                    result = execute_tool(tool_name, tool_input, features)
                    tool_results.append({
                        "tool": tool_name,
                        "input": tool_input,
                        "result": result
                    })
                    
                    # search_knowledge_base 호출 시 즉시 답변 반환 플래그 설정
                    if tool_name == "search_knowledge_base" and "answer" in result:
                        should_return_immediately = True
                        immediate_return_data = {
                            "answer": result["answer"],
                            "tool_results": tool_results,
                            "sources": result.get("sources", [])
                        }
                        break  # 더 이상 도구 실행하지 않음
                    
                    # Tool Result 메시지 구성
                    tool_use_results.append({
                        "toolUseId": tool_use_id,
                        "content": [{"json": result}]
                    })
            
            # search_knowledge_base 결과가 있으면 즉시 반환
            if should_return_immediately:
                return immediate_return_data
            
            # Tool Result를 대화에 추가
            if tool_use_results:
                messages.append({
                    "role": "user",
                    "content": [{"toolResult": tr} for tr in tool_use_results]
                })
    
    # 대화 완료 후 메모리에 저장
    # 사용자 메시지와 최종 응답만 저장
    conversation_memory[session_id].append(current_message)
    if messages:
        last_assistant_message = messages[-1]
        if last_assistant_message.get("role") == "assistant":
            conversation_memory[session_id].append(last_assistant_message)
    
    # 메모리 크기 제한
    if len(conversation_memory[session_id]) > MAX_HISTORY_LENGTH * 2:
        conversation_memory[session_id] = conversation_memory[session_id][-MAX_HISTORY_LENGTH * 2:]
    
    return {
        "answer": "처리 중 오류가 발생했습니다.",
        "tool_results": tool_results
    }

# =============================================================================
# SSE Streaming with Real-time Agent Loop
# =============================================================================
async def agent_event_stream(question: str, features: Dict[str, float], session_id: str = "default"):
    """에이전트 실행을 실시간 SSE로 스트리밍 - 각 단계별로 즉시 전송"""
    import time
    start_time = time.time()

    def elapsed():
        return round(time.time() - start_time, 2)

    try:
        # 세션 메모리 초기화
        if session_id not in conversation_memory:
            conversation_memory[session_id] = []
        
        # 이전 대화 기록 가져오기
        history = conversation_memory[session_id]
        
        # 1. 분석 시작 - 명확한 이벤트 전송
        yield f"data: {json.dumps({'type': 'status', 'message': 'AI 에이전트 시작', 'elapsed': elapsed()}, ensure_ascii=False)}\n\n"
        await asyncio.sleep(0.05)
        
        yield f"data: {json.dumps({'type': 'thinking', 'message': '사용자 질문을 분석하고 있습니다...', 'elapsed': elapsed()}, ensure_ascii=False)}\n\n"
        await asyncio.sleep(0.05)

        # 2. 에이전트 루프 실행 - Generator 버전
        messages = []
        
        # 이전 대화 기록 추가 (최근 MAX_HISTORY_LENGTH개만)
        for msg in history[-MAX_HISTORY_LENGTH:]:
            messages.append(msg)
        
        # 현재 질문 추가 (간결하게 저장)
        current_message = {
            "role": "user",
            "content": [{"text": question}]
        }
        
        # API 호출용 메시지 (상세 정보 포함)
        api_message = {
            "role": "user",
            "content": [
                {
                    "text": f"""사용자 질문: {question}

현재 공정 파라미터:
{json.dumps(features, indent=2, ensure_ascii=False)}

위 질문에 답변하기 위해 필요한 도구를 호출하세요."""
                }
            ]
        }
        messages.append(api_message)

        tool_results_data = []  # 최종 결과 저장

        # Agent Loop - 최대 3회 반복 (도구 호출 → 최종 답변)
        for iteration in range(3):
            # 도구 호출 후 최종 답변 생성 중임을 표시
            if iteration > 0 and tool_use_results:
                yield f"data: {json.dumps({'type': 'status', 'message': '분석 결과를 통합하여 최종 답변 생성 중...', 'elapsed': elapsed()}, ensure_ascii=False)}\n\n"
            else:
                yield f"data: {json.dumps({'type': 'status', 'message': f'도구 선택 중... (반복 {iteration + 1})', 'elapsed': elapsed()}, ensure_ascii=False)}\n\n"
            await asyncio.sleep(0.05)

            # Bedrock Converse API 호출 (동기)
            llm_start = time.time()
            loop = asyncio.get_event_loop()
            response = await loop.run_in_executor(
                None,
                lambda: bedrock_runtime.converse(
                    modelId=MODEL_ID,
                    system=[{"text": SYSTEM_PROMPT}],
                    messages=messages,
                    toolConfig={
                        "tools": [{"toolSpec": tool} for tool in TOOLS]
                    }
                )
            )
            llm_duration = time.time() - llm_start
            print(f"⏱️ LLM 호출 시간: {llm_duration:.2f}초 (iteration {iteration + 1})")

            output = response.get("output", {})
            message = output.get("message", {})
            stop_reason = response.get("stopReason", "")

            # 응답 메시지를 대화에 추가
            messages.append(message)

            # 종료 조건: end_turn이면 최종 응답
            if stop_reason == "end_turn":
                # 텍스트 응답 추출
                final_text = ""
                for content in message.get("content", []):
                    if "text" in content:
                        final_text = content["text"]
                        break

                yield f"data: {json.dumps({'type': 'ai_response', 'data': {'answer': final_text}, 'elapsed': elapsed()}, ensure_ascii=False)}\n\n"
                await asyncio.sleep(0.2)  # 충분한 시간 확보
                yield f"data: {json.dumps({'type': 'done', 'elapsed': elapsed()}, ensure_ascii=False)}\n\n"
                await asyncio.sleep(0.1)  # done 이벤트 전송 확인
                
                # 대화 완료 후 메모리에 저장 (간결한 버전만)
                conversation_memory[session_id].append(current_message)
                # Assistant 응답도 간결하게 저장
                assistant_message = {
                    "role": "assistant",
                    "content": [{"text": final_text}]
                }
                conversation_memory[session_id].append(assistant_message)
                
                # 메모리 크기 제한
                if len(conversation_memory[session_id]) > MAX_HISTORY_LENGTH * 2:
                    conversation_memory[session_id] = conversation_memory[session_id][-MAX_HISTORY_LENGTH * 2:]
                
                return

            # Tool Use 처리
            if stop_reason == "tool_use":
                tool_use_results = []
                kb_answer = None  # KB 검색 결과 저장

                for content in message.get("content", []):
                    if "toolUse" in content:
                        tool_use = content["toolUse"]
                        tool_name = tool_use["name"]
                        tool_input = tool_use.get("input", {})
                        tool_use_id = tool_use["toolUseId"]

                        # ★ Tool 호출 시작 이벤트 전송
                        yield f"data: {json.dumps({'type': 'tool_start', 'tool': tool_name, 'input': tool_input, 'elapsed': elapsed()}, ensure_ascii=False)}\n\n"
                        await asyncio.sleep(0.1)  # 이벤트 확실히 전송

                        # 도구 실행 (동기)
                        result = await loop.run_in_executor(
                            None,
                            execute_tool,
                            tool_name,
                            tool_input,
                            features
                        )

                        # ★ Tool 호출 완료 이벤트 전송
                        yield f"data: {json.dumps({'type': 'tool_end', 'tool': tool_name, 'result': result, 'elapsed': elapsed()}, ensure_ascii=False)}\n\n"
                        await asyncio.sleep(0.1)

                        # ★ 결과 타입별 이벤트 전송 (UI에서 실시간 렌더링)
                        if tool_name == "predict_quality":
                            yield f"data: {json.dumps({'type': 't1_result', 'data': result, 'elapsed': elapsed()}, ensure_ascii=False)}\n\n"
                        elif tool_name == "analyze_feature_importance":
                            yield f"data: {json.dumps({'type': 't2_result', 'data': result, 'elapsed': elapsed()}, ensure_ascii=False)}\n\n"
                        elif tool_name == "search_knowledge_base":
                            yield f"data: {json.dumps({'type': 't3_result', 'data': result, 'elapsed': elapsed()}, ensure_ascii=False)}\n\n"
                            # KB 검색 결과는 즉시 반환
                            if "answer" in result:
                                kb_answer = result["answer"]
                        
                        await asyncio.sleep(0.1)

                        tool_results_data.append({
                            "tool": tool_name,
                            "input": tool_input,
                            "result": result
                        })

                        # Tool Result를 요약해서 LLM에 전달 (토큰 절약)
                        summarized_result = summarize_tool_result(tool_name, result)
                        
                        # Tool Result 메시지 구성
                        tool_use_results.append({
                            "toolUseId": tool_use_id,
                            "content": [{"json": summarized_result}]
                        })

                        await asyncio.sleep(0.1)  # SSE 버퍼 플러시

                # KB 검색 결과가 있으면 즉시 반환 (추가 LLM 호출 없이)
                if kb_answer:
                    yield f"data: {json.dumps({'type': 'ai_response', 'data': {'answer': kb_answer}, 'elapsed': elapsed()}, ensure_ascii=False)}\n\n"
                    await asyncio.sleep(0.2)
                    yield f"data: {json.dumps({'type': 'done', 'elapsed': elapsed()}, ensure_ascii=False)}\n\n"
                    await asyncio.sleep(0.1)
                    
                    # 메모리에 저장
                    conversation_memory[session_id].append(current_message)
                    assistant_message = {
                        "role": "assistant",
                        "content": [{"text": kb_answer}]
                    }
                    conversation_memory[session_id].append(assistant_message)
                    
                    if len(conversation_memory[session_id]) > MAX_HISTORY_LENGTH * 2:
                        conversation_memory[session_id] = conversation_memory[session_id][-MAX_HISTORY_LENGTH * 2:]
                    
                    return

                # Tool Result를 대화에 추가
                if tool_use_results:
                    messages.append({
                        "role": "user",
                        "content": [{"toolResult": tr} for tr in tool_use_results]
                    })
                    
                    # 다음 반복 전 상태 업데이트
                    yield f"data: {json.dumps({'type': 'status', 'message': '도구 결과를 분석하고 있습니다...', 'elapsed': elapsed()}, ensure_ascii=False)}\n\n"
                    await asyncio.sleep(0.05)

        # 대화 완료 후 메모리에 저장 (루프 종료 시)
        conversation_memory[session_id].append(current_message)
        if messages and len(messages) > 0:
            # 마지막 assistant 메시지 찾기
            for msg in reversed(messages):
                if msg.get("role") == "assistant":
                    # 텍스트만 추출해서 저장
                    final_text = ""
                    for content in msg.get("content", []):
                        if "text" in content:
                            final_text = content["text"]
                            break
                    if final_text:
                        assistant_message = {
                            "role": "assistant",
                            "content": [{"text": final_text}]
                        }
                        conversation_memory[session_id].append(assistant_message)
                    break
        
        # 메모리 크기 제한
        if len(conversation_memory[session_id]) > MAX_HISTORY_LENGTH * 2:
            conversation_memory[session_id] = conversation_memory[session_id][-MAX_HISTORY_LENGTH * 2:]
        
        # 최대 반복 초과
        yield f"data: {json.dumps({'type': 'ai_response', 'data': {'answer': '처리 중 최대 반복 횟수를 초과했습니다.'}, 'elapsed': elapsed()}, ensure_ascii=False)}\n\n"
        await asyncio.sleep(0.05)
        yield f"data: {json.dumps({'type': 'done', 'elapsed': elapsed()}, ensure_ascii=False)}\n\n"

    except Exception as e:
        import traceback
        error_detail = traceback.format_exc()
        print(f"Agent Error: {error_detail}")
        yield f"data: {json.dumps({'type': 'error', 'message': str(e), 'elapsed': elapsed()}, ensure_ascii=False)}\n\n"

# =============================================================================
# API Endpoints
# =============================================================================
@app.post("/api/sessions")
async def create_session(req: SessionRequest):
    """세션 생성"""
    return {
        "session_id": f"sess_{req.user_id}_{os.urandom(4).hex()}",
        "created_at": "2026-02-03T15:00:00Z"
    }

@app.post("/api/chat")
async def chat(req: PredictRequest):
    """메인 채팅 엔드포인트 - Bedrock Tool Use 기반"""
    return StreamingResponse(
        agent_event_stream(req.question, req.features, req.session_id),
        media_type="text/event-stream"
    )

@app.get("/health")
async def health():
    return {"status": "healthy", "agent": "bedrock-tool-use"}

# KB Ingest (SigV4 서명 적용)
async def call_lambda_t0(action: str, job_id: Optional[str] = None) -> Dict[str, Any]:
    try:
        payload = {"body": {"action": action}}
        if job_id:
            payload["body"]["job_id"] = job_id
        
        headers = sign_request(LAMBDA_T0_URL, 'POST', payload)
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(LAMBDA_T0_URL, json=payload, headers=headers)
            data = response.json()
            body = data.get("body", data)
            if isinstance(body, str):
                body = json.loads(body)
            return body
    except Exception as e:
        return {"error": str(e)}

@app.post("/api/kb-ingest")
async def kb_ingest(req: KBIngestRequest):
    """KB 인제스트 엔드포인트"""
    result = await call_lambda_t0(req.action, req.job_id)
    return result

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
