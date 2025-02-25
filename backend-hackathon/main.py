from fastapi import FastAPI, UploadFile, Form
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
import boto3
import json
from sentence_transformers import SentenceTransformer
from opensearchpy import OpenSearch

# Khởi tạo AWS services
s3 = boto3.client('s3')
textract = boto3.client('textract')
comprehend = boto3.client('comprehend')
bedrock = boto3.client('bedrock-runtime')
BUCKET_NAME = 'your-s3-bucket-name'  # Thay bằng tên bucket của bạn

# Kết nối OpenSearch (giả sử dùng AWS OpenSearch)
opensearch = OpenSearch(
    hosts=[{'host': 'your-opensearch-endpoint', 'port': 443}],
    http_auth=('username', 'password'),  # Thay bằng thông tin xác thực AWS OpenSearch
    use_ssl=True,
    verify_certs=True
)

# Tải mô hình embedding
embedding_model = SentenceTransformer('all-MiniLM-L6-v2')

# Lifespan handler để thay thế app.on_event("startup")
@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup: Tạo index nếu chưa tồn tại
    if not opensearch.indices.exists(index="patient_notes"):
        opensearch.indices.create(
            index="patient_notes",
            body={
                "settings": {"index": {"knn": True}},
                "mappings": {
                    "properties": {
                        "text": {"type": "text"},
                        "embedding": {"type": "knn_vector", "dimension": 384},
                        "summary": {"type": "text"},
                        "severity": {"type": "keyword"},
                        "treatment": {"type": "text"}
                    }
                }
            }
        )
    yield  # Chuyển giao quyền điều khiển cho ứng dụng
    # Shutdown: Có thể thêm logic cleanup nếu cần (hiện không cần)

# Khởi tạo FastAPI với lifespan
app = FastAPI(lifespan=lifespan)

# Cấu hình CORS để frontend gọi API
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost", "http://localhost:80"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.post("/analyze")
async def analyze_note(file: UploadFile = None, text: str = Form(None)):
    # Step 1: Trích xuất văn bản từ ảnh nếu có (AWS Textract)
    if file:
        # Upload file lên S3
        s3.upload_fileobj(file.file, BUCKET_NAME, file.filename)
        # Gọi Textract để trích xuất văn bản
        response = textract.detect_document_text(
            Document={'S3Object': {'Bucket': BUCKET_NAME, 'Name': file.filename}}
        )
        extracted_text = " ".join([item['Text'] for item in response['Blocks'] if item['BlockType'] == 'LINE'])
    else:
        extracted_text = text

    if not extracted_text:
        return {"error": "Không thể trích xuất nội dung từ ảnh hoặc văn bản rỗng"}

    # Step 2: Phân tích mức độ nghiêm trọng với AWS Comprehend
    sentiment_response = comprehend.detect_sentiment(Text=extracted_text, LanguageCode='en')
    sentiment = sentiment_response['Sentiment']
    if sentiment == 'POSITIVE':
        severity = "Nhẹ"
    elif sentiment == 'NEGATIVE':
        severity = "Nặng"
    else:
        severity = "Trung bình"

    # Step 3: Tóm tắt và đưa ra gợi ý điều trị với AWS Bedrock (Claude)
    prompt = f"""
    Phân tích ghi chú bác sĩ sau: "{extracted_text}"
    1. Tóm tắt nội dung thành một câu ngắn gọn, dễ hiểu.
    2. Đưa ra gợi ý điều trị dựa trên triệu chứng.
    Trả về định dạng JSON với các trường "summary" và "treatment".
    """
    bedrock_response = bedrock.invoke_model(
        modelId='anthropic.claude-v2',  # Hoặc mô hình khác trên Bedrock
        body=json.dumps({
            "prompt": prompt,
            "max_tokens_to_sample": 500,
            "temperature": 0.7
        }),
        contentType='application/json',
        accept='application/json'
    )
    result = json.loads(bedrock_response['body'].read().decode('utf-8'))
    summary = result['completion']['summary']  # Giả định Claude trả về JSON, cần điều chỉnh theo output thực tế
    treatment = result['completion']['treatment']

    # Step 4: Lưu vào OpenSearch
    embedding = embedding_model.encode(extracted_text).tolist()
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

    # Step 5: Trả kết quả
    return {
        "summary": summary,
        "severity": severity,
        "treatment": treatment
    }