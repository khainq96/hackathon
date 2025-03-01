from fastapi import FastAPI, UploadFile, Form
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
import boto3
import json
from opensearchpy import OpenSearch
import os
from PIL import Image
import cv2
import numpy as np
import smtplib
from email.mime.text import MIMEText

# Khởi tạo AWS services
AWS_REGION = os.getenv('AWS_REGION', 'us-east-1')
s3 = boto3.client('s3', region_name=AWS_REGION)
textract = boto3.client('textract', region_name=AWS_REGION)
comprehend = boto3.client('comprehend', region_name=AWS_REGION)
bedrock = boto3.client('bedrock-runtime', region_name=AWS_REGION)
BUCKET_NAME = os.getenv('S3_BUCKET', 'your-s3-bucket-name')

# Cấu hình OpenSearch
OPENSEARCH_HOST = os.getenv('OPENSEARCH_HOST', 'localhost')
OPENSEARCH_PORT = int(os.getenv('OPENSEARCH_PORT', 9200))
OPENSEARCH_USERNAME = os.getenv('OPENSEARCH_USERNAME', 'admin')
OPENSEARCH_PASSWORD = os.getenv('OPENSEARCH_PASSWORD', 'admin')
OPENSEARCH_USE_SSL = os.getenv('OPENSEARCH_USE_SSL', 'false').lower() == 'true'

opensearch = OpenSearch(
    hosts=[{'host': OPENSEARCH_HOST, 'port': OPENSEARCH_PORT}],
    http_auth=(OPENSEARCH_USERNAME, OPENSEARCH_PASSWORD),
    use_ssl=OPENSEARCH_USE_SSL,
    verify_certs=OPENSEARCH_USE_SSL
)

app = FastAPI()

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost", "http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Tiền xử lý ảnh
def preprocess_image(file):
    img = Image.open(file.file).convert('L')  # Grayscale
    img_cv = np.array(img)
    img_cv = cv2.threshold(img_cv, 128, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)[1]  # Binarization
    return Image.fromarray(img_cv)

# Gửi email cảnh báo
def send_alert(email, text, severity):
    if severity == "Nặng":
        msg = MIMEText(f"Cảnh báo: Ghi chú mới với mức độ nghiêm trọng Nặng:\n{text}")
        msg['Subject'] = "Cảnh báo Ghi chú Bác sĩ"
        msg['From'] = "system@example.com"
        msg['To'] = email
        with smtplib.SMTP('smtp.example.com') as smtp:  # Thay bằng SMTP server của bạn
            smtp.send_message(msg)

# Lấy embedding từ Bedrock
def get_embedding(text: str):
    try:
        response = bedrock.invoke_model(
            modelId='amazon.titan-embeddings-text-v1',
            body=json.dumps({"inputText": text}),
            contentType='application/json',
            accept='application/json'
        )
        result = json.loads(response['body'].read().decode('utf-8'))
        return result['embedding']
    except Exception as e:
        print(f"Error in get_embedding: {str(e)}")
        raise

# Tìm kiếm ghi chú tương tự từ OpenSearch
def search_similar_notes(embedding, severity=None, top_k=3):
    try:
        query = {
            "query": {
                "knn": {
                    "embedding": {
                        "vector": embedding,
                        "k": top_k
                    }
                }
            }
        }
        if severity:  # Lọc theo mức độ nghiêm trọng
            query["query"] = {
                "bool": {
                    "filter": {"term": {"severity": severity}},
                    "must": query["query"]
                }
            }
        response = opensearch.search(index="patient_notes", body=query)
        hits = response['hits']['hits']
        return [{"text": hit['_source']['text'], "summary": hit['_source']['summary'], "treatment": hit['_source']['treatment'], "score": hit['_score']} for hit in hits]
    except Exception as e:
        print(f"Error in search_similar_notes: {str(e)}")
        return []

@app.post("/analyze")
async def analyze_note(file: UploadFile = None, text: str = Form(None)):
    if file:
        processed_img = preprocess_image(file)
        processed_img.save(f"/tmp/{file.filename}")
        s3.upload_file(f"/tmp/{file.filename}", BUCKET_NAME, file.filename)
        response = textract.detect_document_text(
            Document={'S3Object': {'Bucket': BUCKET_NAME, 'Name': file.filename}}
        )
        extracted_text = " ".join([item['Text'] for item in response['Blocks'] if item['BlockType'] == 'LINE'])
    else:
        extracted_text = text

    if not extracted_text or len(extracted_text) > 10000:
        extracted_text = extracted_text[:10000] if extracted_text else ""
        return {"error": "Không thể trích xuất nội dung hoặc văn bản quá dài"}

    # Tạo embedding
    embedding = get_embedding(extracted_text)

    # Phân tích mức độ nghiêm trọng
    sentiment_response = comprehend.detect_sentiment(Text=extracted_text, LanguageCode='en')
    sentiment = sentiment_response['Sentiment']
    severity = "Nhẹ" if sentiment == 'POSITIVE' else "Nặng" if sentiment == 'NEGATIVE' else "Trung bình"

    # Tìm kiếm ghi chú tương tự
    similar_notes = search_similar_notes(embedding, severity)

    # Tạo prompt với RAG
    similar_context = "\n".join([f"- {note['text']} (Tóm tắt: {note['summary']}, Điều trị: {note['treatment']}, Độ tương đồng: {note['score']})" for note in similar_notes])
    prompt = f"""
    Dưới đây là ghi chú bác sĩ mới: "{extracted_text}"
    Dựa trên ghi chú này và các trường hợp tương tự sau:
    {similar_context if similar_context else "Không có trường hợp tương tự."}

    1. Tóm tắt nội dung thành một câu ngắn gọn, dễ hiểu.
    2. Đưa ra gợi ý điều trị dựa trên triệu chứng và các trường hợp tương tự (nếu có).
    Trả về định dạng JSON với các trường "summary" và "treatment".
    """
    try:
        bedrock_response = bedrock.invoke_model(
            modelId='anthropic.claude-3-haiku-20240307-v1:0',
            body=json.dumps({
                "prompt": f"\n\nHuman: {prompt} \n\nAssistant: ",
                "max_tokens": 500,
                "temperature": 0.7
            }),
            contentType='application/json',
            accept='application/json'
        )
        result = json.loads(bedrock_response['body'].read().decode('utf-8'))
        summary = result.get('content', [{}])[0].get('text', '').split('"summary":')[1].split('"treatment":')[0].strip('", ')
        treatment = result.get('content', [{}])[0].get('text', '').split('"treatment":')[1].strip('"} ')
    except Exception as e:
        print(f"Error in Bedrock call: {str(e)}")
        return {"error": f"Bedrock error: {str(e)}"}

    # Gửi thông báo nếu nghiêm trọng
    send_alert("doctor@example.com", extracted_text, severity)

    # Lưu vào OpenSearch
    opensearch.index(
        index='patient_notes',
        body={
            'text': extracted_text,
            'embedding': embedding,
            'summary': summary,
            'severity': severity,
            'treatment': treatment
        }
    )

    return {
        "summary": summary,
        "severity": severity,
        "treatment": treatment,
        "similar_notes": similar_notes
    }

@app.get("/search")
async def search_notes(query: str):
    try:
        response = opensearch.search(
            index="patient_notes",
            body={
                "query": {
                    "match": {
                        "text": query
                    }
                }
            }
        )
        return {"results": [hit['_source'] for hit in response['hits']['hits']]}
    except Exception as e:
        return {"error": str(e)}