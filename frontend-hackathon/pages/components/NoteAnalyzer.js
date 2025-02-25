import React, { useState } from 'react';
import axios from 'axios';

function NoteAnalyzer() {
  const [file, setFile] = useState(null);
  const [text, setText] = useState('');
  const [result, setResult] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);

  const handleSubmit = async (e) => {
    e.preventDefault();
    setLoading(true);
    setError(null);
    setResult(null);

    const formData = new FormData();
    if (file) formData.append('file', file);
    if (text) formData.append('text', text);

    try {
      const response = await axios.post('http://localhost:8000/analyze', formData, {
        headers: { 'Content-Type': 'multipart/form-data' },
      });
      setResult(response.data);
    } catch (err) {
      setError('Có lỗi xảy ra khi phân tích. Vui lòng thử lại.');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div>
      <form onSubmit={handleSubmit}>
        <div>
          <label>Upload ảnh ghi chú:</label>
          <input
            type="file"
            accept=".jpg,.png,.pdf"
            onChange={(e) => setFile(e.target.files[0])}
          />
        </div>
        <div>
          <label>Hoặc nhập văn bản:</label>
          <textarea
            value={text}
            onChange={(e) => setText(e.target.value)}
            placeholder="Nhập ghi chú bác sĩ..."
            rows={5}
            cols={50}
          />
        </div>
        <button type="submit" disabled={loading}>
          {loading ? 'Đang xử lý...' : 'Phân tích'}
        </button>
      </form>

      {error && <p style={{ color: 'red' }}>{error}</p>}
      {result && (
        <div>
          <h3>Tóm tắt:</h3>
          <p>{result.summary}</p>
          <h3>Mức độ nghiêm trọng:</h3>
          <p>{result.severity}</p>
          <h3>Gợi ý điều trị:</h3>
          <p>{result.treatment}</p>
        </div>
      )}
    </div>
  );
}

export default NoteAnalyzer;