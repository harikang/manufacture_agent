"""
Lambda T0: Knowledge Base Ingest
문서 청킹, 임베딩 후 S3 Vector 인덱스 및 Knowledge Base 메타데이터 갱신
"""
import json
import boto3
import os
from datetime import datetime

# AWS Clients
bedrock_agent = boto3.client('bedrock-agent', region_name='us-east-1')

# Environment Variables
KNOWLEDGE_BASE_ID = os.getenv('KNOWLEDGE_BASE_ID', 'YOUR_KNOWLEDGE_BASE_ID')
DATA_SOURCE_ID = os.getenv('DATA_SOURCE_ID', '85CWXCHZLJ')


def lambda_handler(event, context):
    """
    KB 인제스트 워크플로우 실행
    1. Data Source 동기화 시작 (Ingestion Job)
    2. 문서 청킹 및 임베딩 (Bedrock 자동 처리)
    3. S3 Vector 인덱스 갱신
    """
    try:
        # Parse request
        body = event.get('body', {})
        if isinstance(body, str):
            body = json.loads(body)
        
        action = body.get('action', 'start_ingestion')
        
        if action == 'start_ingestion':
            return start_ingestion_job()
        elif action == 'check_status':
            job_id = body.get('job_id')
            return check_ingestion_status(job_id)
        elif action == 'list_jobs':
            return list_ingestion_jobs()
        else:
            return response(400, {'error': f'Unknown action: {action}'})
            
    except Exception as e:
        print(f"Error: {str(e)}")
        return response(500, {'error': str(e)})


def start_ingestion_job():
    """Data Source 동기화 시작"""
    try:
        result = bedrock_agent.start_ingestion_job(
            knowledgeBaseId=KNOWLEDGE_BASE_ID,
            dataSourceId=DATA_SOURCE_ID
        )
        
        job = result.get('ingestionJob', {})
        
        return response(200, {
            'message': 'Ingestion job started successfully',
            'job_id': job.get('ingestionJobId'),
            'status': job.get('status'),
            'started_at': job.get('startedAt', datetime.now()).isoformat() if job.get('startedAt') else datetime.now().isoformat(),
            'knowledge_base_id': KNOWLEDGE_BASE_ID,
            'data_source_id': DATA_SOURCE_ID
        })
        
    except Exception as e:
        return response(500, {
            'error': f'Failed to start ingestion job: {str(e)}'
        })


def check_ingestion_status(job_id):
    """Ingestion Job 상태 확인"""
    if not job_id:
        return response(400, {'error': 'job_id is required'})
    
    try:
        result = bedrock_agent.get_ingestion_job(
            knowledgeBaseId=KNOWLEDGE_BASE_ID,
            dataSourceId=DATA_SOURCE_ID,
            ingestionJobId=job_id
        )
        
        job = result.get('ingestionJob', {})
        statistics = job.get('statistics', {})
        
        return response(200, {
            'job_id': job.get('ingestionJobId'),
            'status': job.get('status'),
            'started_at': job.get('startedAt').isoformat() if job.get('startedAt') else None,
            'updated_at': job.get('updatedAt').isoformat() if job.get('updatedAt') else None,
            'statistics': {
                'documents_scanned': statistics.get('numberOfDocumentsScanned', 0),
                'documents_indexed': statistics.get('numberOfNewDocumentsIndexed', 0),
                'documents_modified': statistics.get('numberOfModifiedDocumentsIndexed', 0),
                'documents_deleted': statistics.get('numberOfDocumentsDeleted', 0),
                'documents_failed': statistics.get('numberOfDocumentsFailed', 0)
            },
            'failure_reasons': job.get('failureReasons', [])
        })
        
    except Exception as e:
        return response(500, {
            'error': f'Failed to get ingestion status: {str(e)}'
        })


def list_ingestion_jobs():
    """최근 Ingestion Job 목록 조회"""
    try:
        result = bedrock_agent.list_ingestion_jobs(
            knowledgeBaseId=KNOWLEDGE_BASE_ID,
            dataSourceId=DATA_SOURCE_ID,
            maxResults=10,
            sortBy={
                'attribute': 'STARTED_AT',
                'order': 'DESCENDING'
            }
        )
        
        jobs = []
        for job in result.get('ingestionJobSummaries', []):
            jobs.append({
                'job_id': job.get('ingestionJobId'),
                'status': job.get('status'),
                'started_at': job.get('startedAt').isoformat() if job.get('startedAt') else None,
                'updated_at': job.get('updatedAt').isoformat() if job.get('updatedAt') else None
            })
        
        return response(200, {
            'jobs': jobs,
            'knowledge_base_id': KNOWLEDGE_BASE_ID,
            'data_source_id': DATA_SOURCE_ID
        })
        
    except Exception as e:
        return response(500, {
            'error': f'Failed to list ingestion jobs: {str(e)}'
        })


def response(status_code, body):
    """API Gateway 응답 포맷"""
    return {
        'statusCode': status_code,
        'headers': {
            'Content-Type': 'application/json',
            'Access-Control-Allow-Origin': '*',
            'Access-Control-Allow-Headers': 'Content-Type',
            'Access-Control-Allow-Methods': 'POST, OPTIONS'
        },
        'body': json.dumps(body, ensure_ascii=False)
    }
