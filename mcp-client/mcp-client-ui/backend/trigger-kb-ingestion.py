#!/usr/bin/env python3
"""
Direct Bedrock KB Ingestion Trigger

Simple script to trigger ingestion jobs directly without Lambda functions.
"""

import boto3
import json
import os
import sys
from datetime import datetime
from dotenv import load_dotenv

# Load environment variables from current directory
load_dotenv('.env')

def trigger_ingestion(kb_id: str, data_source_id: str, project_name: str = None):
    """Trigger a Bedrock KB ingestion job directly."""
    
    bedrock_agent = boto3.client('bedrock-agent', region_name='us-east-1')
    
    try:
        description = f'Direct ingestion job'
        if project_name:
            description += f' for project {project_name}'
        description += f' - {datetime.now().isoformat()}'
        
        print(f"🚀 Starting ingestion job...")
        print(f"   KB ID: {kb_id}")
        print(f"   Data Source ID: {data_source_id}")
        if project_name:
            print(f"   Project: {project_name}")
        
        response = bedrock_agent.start_ingestion_job(
            knowledgeBaseId=kb_id,
            dataSourceId=data_source_id,
            description=description
        )
        
        job_id = response['ingestionJob']['ingestionJobId']
        status = response['ingestionJob']['status']
        
        print(f"✅ Ingestion job started successfully!")
        print(f"   Job ID: {job_id}")
        print(f"   Status: {status}")
        
        return job_id
        
    except Exception as e:
        print(f"❌ Error starting ingestion job: {e}")
        return None

def check_ingestion_status(kb_id: str, data_source_id: str, job_id: str):
    """Check the status of an ingestion job."""
    
    bedrock_agent = boto3.client('bedrock-agent', region_name='us-east-1')
    
    try:
        response = bedrock_agent.get_ingestion_job(
            knowledgeBaseId=kb_id,
            dataSourceId=data_source_id,
            ingestionJobId=job_id
        )
        
        job = response['ingestionJob']
        status = job['status']
        
        print(f"📊 Ingestion Job Status: {status}")
        
        if 'statistics' in job:
            stats = job['statistics']
            print(f"   Documents processed: {stats.get('numberOfDocumentsScanned', 0)}")
            print(f"   Documents indexed: {stats.get('numberOfNewDocumentsIndexed', 0)}")
            print(f"   Documents updated: {stats.get('numberOfModifiedDocumentsIndexed', 0)}")
            print(f"   Documents deleted: {stats.get('numberOfDocumentsDeleted', 0)}")
        
        if 'failureReasons' in job and job['failureReasons']:
            print("⚠️  Failure reasons:")
            for reason in job['failureReasons']:
                print(f"   - {reason}")
        
        return status
        
    except Exception as e:
        print(f"❌ Error checking ingestion status: {e}")
        return None

def list_recent_jobs(kb_id: str, data_source_id: str, max_results: int = 5):
    """List recent ingestion jobs."""
    
    bedrock_agent = boto3.client('bedrock-agent', region_name='us-east-1')
    
    try:
        response = bedrock_agent.list_ingestion_jobs(
            knowledgeBaseId=kb_id,
            dataSourceId=data_source_id,
            maxResults=max_results
        )
        
        jobs = response.get('ingestionJobSummaries', [])
        
        if not jobs:
            print("📋 No recent ingestion jobs found")
            return
        
        print(f"📋 Recent ingestion jobs ({len(jobs)}):")
        print("-" * 80)
        
        for job in jobs:
            job_id = job['ingestionJobId']
            status = job['status']
            started = job.get('startedAt', 'Unknown')
            updated = job.get('updatedAt', 'Unknown')
            
            print(f"Job ID: {job_id}")
            print(f"Status: {status}")
            print(f"Started: {started}")
            print(f"Updated: {updated}")
            
            if 'statistics' in job:
                stats = job['statistics']
                print(f"Documents: {stats.get('numberOfDocumentsScanned', 0)} scanned, "
                      f"{stats.get('numberOfNewDocumentsIndexed', 0)} indexed")
            
            print("-" * 40)
        
    except Exception as e:
        print(f"❌ Error listing ingestion jobs: {e}")

def main():
    """Main function to handle command line arguments."""
    
    # Load environment variables from backend .env file
    env_file_path = 'backend/.env'
    if os.path.exists(env_file_path):
        with open(env_file_path, 'r') as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith('#') and '=' in line:
                    key, value = line.split('=', 1)
                    os.environ[key] = value
    
    # Get configuration from environment or use existing KB
    kb_id = os.getenv('BEDROCK_KNOWLEDGE_BASE_ID')  # KB ID from environment
    data_source_id = os.getenv('BEDROCK_DATA_SOURCE_ID')  # Data source ID from environment
    
    if len(sys.argv) > 1:
        command = sys.argv[1].lower()
        
        if command == 'start':
            project_name = sys.argv[2] if len(sys.argv) > 2 else None
            if not kb_id or not data_source_id:
                print("❌ Please set BEDROCK_KNOWLEDGE_BASE_ID and BEDROCK_DATA_SOURCE_ID environment variables")
                return
            
            job_id = trigger_ingestion(kb_id, data_source_id, project_name)
            if job_id:
                print(f"\n💡 To check status: python {sys.argv[0]} status {job_id}")
        
        elif command == 'status':
            job_id = sys.argv[2] if len(sys.argv) > 2 else None
            if not job_id:
                print("❌ Please provide job ID: python trigger-kb-ingestion.py status <job_id>")
                return
            
            if not kb_id or not data_source_id:
                print("❌ Please set BEDROCK_KNOWLEDGE_BASE_ID and BEDROCK_DATA_SOURCE_ID environment variables")
                return
            
            check_ingestion_status(kb_id, data_source_id, job_id)
        
        elif command == 'list':
            if not kb_id or not data_source_id:
                print("❌ Please set BEDROCK_KNOWLEDGE_BASE_ID and BEDROCK_DATA_SOURCE_ID environment variables")
                return
            
            list_recent_jobs(kb_id, data_source_id)
        
        else:
            print("❌ Unknown command. Use: start, status, or list")
    
    else:
        print("🔧 Bedrock KB Ingestion Tool")
        print("=" * 40)
        print("Usage:")
        print("  python trigger-kb-ingestion.py start [project_name]  - Start ingestion job")
        print("  python trigger-kb-ingestion.py status <job_id>       - Check job status")
        print("  python trigger-kb-ingestion.py list                  - List recent jobs")
        print()
        print("Environment variables required:")
        print("  BEDROCK_KNOWLEDGE_BASE_ID")
        print("  BEDROCK_DATA_SOURCE_ID")

if __name__ == "__main__":
    main()