"""
Lambda T3 (RAG) 테스트 스크립트
"""

import requests
import json
import sys

# Lambda T3 URL 읽기
try:
    with open('lambda_t3_url.txt', 'r') as f:
        LAMBDA_URL = f.read().strip()
except FileNotFoundError:
    print("✗ lambda_t3_url.txt 파일을 찾을 수 없습니다.")
    print("먼저 deploy_lambda_t3.sh를 실행하세요.")
    sys.exit(1)

print(f"Lambda T3 URL: {LAMBDA_URL}")
print("=" * 60)

# 테스트 케이스
test_cases = [
    {
        "name": "트러블슈팅 질문",
        "payload": {
            "query": "포로시티 불량이 발생했을 때 어떻게 해결하나요?",
            "use_knowledge_base": True
        }
    },
    {
        "name": "공정 파라미터 질문",
        "payload": {
            "query": "주입 속도의 권장 범위는 얼마인가요?",
            "use_knowledge_base": True
        }
    },
    {
        "name": "안전 규정 질문",
        "payload": {
            "query": "용탕 취급 시 필수 보호구는 무엇인가요?",
            "use_knowledge_base": True
        }
    },
    {
        "name": "센서 정보 질문",
        "payload": {
            "query": "온도 센서의 측정 범위는 어떻게 되나요?",
            "use_knowledge_base": True
        }
    }
]

# 테스트 실행
for i, test_case in enumerate(test_cases, 1):
    print(f"\n[테스트 {i}/{len(test_cases)}] {test_case['name']}")
    print("-" * 60)
    print(f"질문: {test_case['payload']['query']}")
    
    try:
        response = requests.post(
            LAMBDA_URL,
            headers={'Content-Type': 'application/json'},
            json=test_case['payload'],
            timeout=60
        )
        
        if response.status_code == 200:
            result = response.json()
            
            print(f"\n✓ 응답 성공 (처리 시간: {result.get('processing_time_ms', 0):.2f}ms)")
            print(f"Knowledge Base 사용: {result.get('used_knowledge_base', False)}")
            print(f"\n답변:")
            print(result['answer'])
            
            if 'sources' in result and result['sources']:
                print(f"\n출처 ({len(result['sources'])}개):")
                for j, source in enumerate(result['sources'], 1):
                    print(f"  {j}. 관련도: {source.get('score', 0):.3f}")
                    print(f"     내용: {source['content_preview'][:150]}...")
        else:
            print(f"\n✗ 응답 실패 (상태 코드: {response.status_code})")
            print(f"에러: {response.text}")
    
    except Exception as e:
        print(f"\n✗ 테스트 실패: {str(e)}")

print("\n" + "=" * 60)
print("테스트 완료!")
print("=" * 60)
