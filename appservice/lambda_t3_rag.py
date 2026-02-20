"""
Lambda T3: RAG 기반 질의응답
- S3에 저장된 문서 활용
- Amazon Bedrock Knowledge Bases 연동
- 공정 SOP, 장비 설명, 센서 정의, 트러블슈팅 노트 등
"""

import json
import boto3
import time
import os
from typing import Dict, Any, List
from datetime import datetime

# AWS clients
s3 = boto3.client('s3')
bedrock_agent_runtime = boto3.client('bedrock-agent-runtime', region_name='us-east-1')
bedrock_runtime = boto3.client('bedrock-runtime', region_name='us-east-1')

# Configuration (환경변수로 설정 필요)
BUCKET_NAME = os.environ.get('BUCKET_NAME', 'your-knowledge-base-bucket')
KNOWLEDGE_BASE_ID = os.environ.get('KNOWLEDGE_BASE_ID', 'YOUR_KNOWLEDGE_BASE_ID')
MODEL_ID = 'us.anthropic.claude-sonnet-4-5-20250929-v1:0'  # Claude Sonnet 4.5 (US inference profile)

# Document categories in S3 (flat structure - all docs in root)
DOCUMENT_PREFIXES = {
    'sop': '',  # diecasting_process_sop.md, injection_process_sop.md
    'equipment': '',  # diecasting_machine_specs.md
    'sensors': '',  # sensor_specifications.md, sensor_calibration_guide.md
    'troubleshooting': '',  # defect_analysis.md, porosity_troubleshooting_guide.md
    'quality': ''  # quality_standards.md, process_parameter_guidelines.md
}

# Document name patterns for category inference
DOCUMENT_PATTERNS = {
    'sop': ['sop', 'process'],
    'equipment': ['machine', 'specs'],
    'sensors': ['sensor'],
    'troubleshooting': ['defect', 'troubleshooting', 'porosity'],
    'quality': ['quality', 'parameter', 'guidelines'],
    'safety': ['safety', 'regulations']
}


def retrieve_from_knowledge_base(query: str, max_results: int = 5) -> List[Dict]:
    """
    Bedrock Knowledge Base에서 관련 문서 검색
    """
    try:
        response = bedrock_agent_runtime.retrieve(
            knowledgeBaseId=KNOWLEDGE_BASE_ID,
            retrievalQuery={
                'text': query
            },
            retrievalConfiguration={
                'vectorSearchConfiguration': {
                    'numberOfResults': max_results
                }
            }
        )
        
        results = []
        for result in response.get('retrievalResults', []):
            # S3 location 정보 추출
            location = result.get('location', {})
            s3_location = location.get('s3Location', {})
            
            # 메타데이터 추출
            metadata = result.get('metadata', {})
            
            results.append({
                'content': result['content']['text'],
                'score': result.get('score', 0),
                'location': s3_location,
                'uri': s3_location.get('uri', ''),
                'metadata': metadata,
                'source_type': metadata.get('x-amz-bedrock-kb-source-type', 'unknown'),
                'document_id': metadata.get('x-amz-bedrock-kb-document-id', ''),
            })
        
        return results
    
    except Exception as e:
        print(f"Knowledge Base retrieval error: {e}")
        import traceback
        traceback.print_exc()
        return []


def retrieve_from_s3_direct(query: str, category: str = None) -> List[Dict]:
    """
    S3에서 직접 문서 검색 (Knowledge Base 없이)
    - 모든 문서가 버킷 루트에 있는 flat 구조
    """
    try:
        # S3 객체 리스트 (루트에서 모든 .md 파일)
        response = s3.list_objects_v2(
            Bucket=BUCKET_NAME,
            MaxKeys=20
        )
        
        results = []
        query_keywords = query.lower().split()
        
        for obj in response.get('Contents', []):
            key = obj['Key']
            if not key.endswith('.md'):
                continue
            
            # 카테고리 필터링 (지정된 경우)
            if category and category in DOCUMENT_PATTERNS:
                patterns = DOCUMENT_PATTERNS[category]
                if not any(p in key.lower() for p in patterns):
                    continue
            
            # 문서 내용 읽기
            try:
                doc_response = s3.get_object(Bucket=BUCKET_NAME, Key=key)
                content = doc_response['Body'].read().decode('utf-8')
                
                # 키워드 매칭 점수 계산
                content_lower = content.lower()
                match_score = sum(1 for kw in query_keywords if kw in content_lower)
                
                if match_score > 0:
                    results.append({
                        'content': content[:1500],  # 처음 1500자
                        'key': key,
                        'size': obj['Size'],
                        'score': match_score / len(query_keywords),
                        'uri': f's3://{BUCKET_NAME}/{key}'
                    })
            except Exception as e:
                print(f"Error reading {key}: {e}")
                continue
        
        # 점수순 정렬
        results.sort(key=lambda x: x['score'], reverse=True)
        return results[:5]  # 상위 5개
    
    except Exception as e:
        print(f"S3 direct retrieval error: {e}")
        return []


def infer_category_from_query(query: str) -> str:
    """
    쿼리에서 카테고리 추론
    """
    query_lower = query.lower()
    
    if any(kw in query_lower for kw in ['불량', '원인', '문제', 'defect', 'issue', '포로시티', 'porosity']):
        return 'troubleshooting'
    elif any(kw in query_lower for kw in ['센서', 'sensor', '측정', '교정', 'calibration']):
        return 'sensors'
    elif any(kw in query_lower for kw in ['장비', 'equipment', '기계', 'machine', '스펙']):
        return 'equipment'
    elif any(kw in query_lower for kw in ['절차', 'sop', '프로세스', 'process', '공정']):
        return 'sop'
    elif any(kw in query_lower for kw in ['안전', 'safety', '규정']):
        return 'safety'
    else:
        return 'quality'


def generate_answer_with_bedrock(query: str, context: List[Dict], 
                                 additional_context: Dict = None) -> str:
    """
    Bedrock Claude를 사용하여 답변 생성 (메타데이터 활용)
    """
    try:
        # Context 문서 결합 (메타데이터 포함)
        context_parts = []
        for i, doc in enumerate(context[:3]):
            doc_text = f"[문서 {i+1}]"
            
            # 문서 출처 정보 추가
            if doc.get('uri'):
                doc_text += f"\n출처: {doc['uri']}"
            if doc.get('source_type'):
                doc_text += f"\n유형: {doc['source_type']}"
            
            doc_text += f"\n관련도: {doc.get('score', 0):.2f}"
            doc_text += f"\n\n{doc['content'][:500]}"
            context_parts.append(doc_text)
        
        context_text = "\n\n".join(context_parts)
        
        # 추가 컨텍스트 (예측 결과 등)
        extra_info = ""
        if additional_context:
            if 'last_prediction' in additional_context:
                pred = additional_context['last_prediction']
                extra_info += f"\n\n[최근 예측 결과]\n"
                extra_info += f"- 예측: {pred['prediction']['class']}\n"
                extra_info += f"- 확률: {pred['prediction']['probability']:.1%}\n"
        
        # 프롬프트 생성
        prompt = f"""당신은 다이캐스팅 품질 관리 전문가입니다. 다음 문서들을 참고하여 질문에 답변해주세요.

[참고 문서]
{context_text}
{extra_info}

[질문]
{query}

[답변 가이드라인]
- 참고 문서의 내용을 기반으로 답변하세요
- 구체적이고 실용적인 정보를 제공하세요
- 불확실한 경우 추가 정보가 필요하다고 말하세요
- 300자 이내로 간결하게 답변하세요

답변:"""
        
        # Bedrock Claude 호출
        body = json.dumps({
            "anthropic_version": "bedrock-2023-05-31",
            "max_tokens": 1000,
            "messages": [
                {
                    "role": "user",
                    "content": prompt
                }
            ],
            "temperature": 0.7
        })
        
        response = bedrock_runtime.invoke_model(
            modelId=MODEL_ID,
            body=body
        )
        
        response_body = json.loads(response['body'].read())
        answer = response_body['content'][0]['text']
        
        return answer.strip()
    
    except Exception as e:
        print(f"Bedrock answer generation error: {e}")
        return generate_fallback_answer(query)


def generate_fallback_answer(query: str) -> str:
    """
    Bedrock 사용 불가 시 기본 답변
    """
    query_lower = query.lower()
    
    # 키워드 기반 답변
    if '불량' in query_lower or 'defect' in query_lower:
        return """다이캐스팅 불량의 주요 원인:

1. **온도 관리 문제**
   - 용탕 온도 과다/부족
   - 금형 온도 불균형

2. **압력 제어 문제**
   - 사출 압력 부적절
   - 보압 시간 미흡

3. **냉각 시간 부족**

개선 방안: 온도/압력 센서 정기 점검, 공정 파라미터 최적화"""
    
    elif '개선' in query_lower or 'improve' in query_lower:
        return """품질 개선 권장사항:

1. **공정 최적화**
   - 온도: 650-680°C 유지
   - 압력: 120-130 MPa 범위
   - 냉각 시간: 15초 이상

2. **예방 정비**
   - 센서 교정 (월 1회)
   - 금형 청소 (주 1회)

3. **실시간 모니터링**
   - AI 예측 시스템 활용
   - 이상 패턴 조기 감지"""
    
    elif '센서' in query_lower or 'sensor' in query_lower:
        return """주요 센서 정보:

1. **온도 센서** (Temperature1-3)
   - 용탕, 금형, 냉각수 온도 측정
   - 정확도: ±2°C

2. **압력 센서** (Pressure1-3)
   - 사출, 보압, 배압 측정
   - 범위: 0-200 MPa

3. **진동 센서** (Vibration)
   - 장비 상태 모니터링
   - 이상 진동 감지"""
    
    else:
        return """안녕하세요! 다이캐스팅 품질 예측 AI 어시스턴트입니다.

다음 주제에 대해 질문해주세요:
- 불량 원인 분석
- 품질 개선 방안
- 센서 및 장비 정보
- 공정 파라미터 최적화
- 트러블슈팅 가이드

구체적인 질문을 해주시면 더 자세히 답변드리겠습니다."""


def lambda_handler(event, context):
    """
    Lambda 핸들러
    
    Input:
        {
            "query": "불량의 주요 원인은?",
            "use_knowledge_base": true,  # optional
            "context": {...}  # optional (예측 결과 등)
        }
    
    Output:
        {
            "statusCode": 200,
            "body": {
                "answer": "...",
                "sources": [...],
                "processing_time_ms": 123.45
            }
        }
    """
    start_time = time.time()
    
    try:
        # 입력 파싱
        if isinstance(event.get('body'), str):
            body = json.loads(event['body'])
        else:
            body = event.get('body', event)
        
        # body가 또 다른 body를 포함하는 경우 처리 (중첩 구조)
        if 'body' in body and isinstance(body['body'], dict):
            body = body['body']
        
        query = body.get('query', '')
        use_knowledge_base = body.get('use_knowledge_base', True)
        additional_context = body.get('context')
        
        if not query:
            return {
            'statusCode': 400,
            'headers': {
                'Content-Type': 'application/json'
            },
            'body': json.dumps({
                'error': 'Query is required'
            })
        }
        
        # 문서 검색
        if use_knowledge_base:
            retrieved_docs = retrieve_from_knowledge_base(query)
        else:
            retrieved_docs = retrieve_from_s3_direct(query)
        
        # 답변 생성
        if retrieved_docs:
            answer = generate_answer_with_bedrock(query, retrieved_docs, additional_context)
            sources = [
                {
                    'content_preview': doc['content'][:200],
                    'score': doc.get('score', 0),
                    'uri': doc.get('uri', ''),
                    'source_type': doc.get('source_type', 'unknown'),
                    'title': doc.get('uri', '').split('/')[-1] if doc.get('uri') else 'N/A'
                }
                for doc in retrieved_docs[:3]
            ]
        else:
            answer = generate_fallback_answer(query)
            sources = []
        
        # 처리 시간
        processing_time = (time.time() - start_time) * 1000
        
        # 응답 생성
        response_body = {
            'answer': answer,
            'sources': sources,
            'processing_time_ms': round(processing_time, 2),
            'timestamp': datetime.utcnow().isoformat(),
            'used_knowledge_base': use_knowledge_base and len(retrieved_docs) > 0
        }
        
        return {
            'statusCode': 200,
            'headers': {
                'Content-Type': 'application/json'
            },
            'body': json.dumps(response_body, ensure_ascii=False)
        }
    
    except Exception as e:
        print(f"Error: {str(e)}")
        return {
            'statusCode': 500,
            'headers': {
                'Content-Type': 'application/json'
            },
            'body': json.dumps({
                'error': 'Internal server error',
                'message': str(e)
            })
        }


# Local testing
if __name__ == '__main__':
    test_event = {
        'body': {
            'query': '불량의 주요 원인은?',
            'use_knowledge_base': False  # Set to True to test Knowledge Base
        }
    }
    
    result = lambda_handler(test_event, None)
    print(json.dumps(json.loads(result['body']), indent=2, ensure_ascii=False))
