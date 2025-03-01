import React, { useState } from 'react';
import axios from 'axios';

function NoteAnalyzer() {
  const [file, setFile] = useState(null);
  const [text, setText] = useState('');
  const [result, setResult] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const [expandedNotes, setExpandedNotes] = useState({});

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

  const toggleNote = (index) => {
    setExpandedNotes((prev) => ({
      ...prev,
      [index]: !prev[index],
    }));
  };

  return (
    <div className="space-y-6 bg-white p-6 rounded-lg shadow">
      <form onSubmit={handleSubmit} className="space-y-4">
        <div>
          <label className="block text-sm font-medium text-gray-700">Upload ảnh ghi chú:</label>
          <input
            type="file"
            accept=".jpg,.png,.pdf"
            onChange={(e) => setFile(e.target.files[0])}
            className="mt-1 block w-full text-sm text-gray-500 file:mr-4 file:py-2 file:px-4 file:rounded-md file:border-0 file:text-sm file:font-semibold file:bg-blue-50 file:text-blue-700 hover:file:bg-blue-100"
          />
        </div>
        <div>
          <label className="block text-sm font-medium text-gray-700">Hoặc nhập văn bản:</label>
          <textarea
            value={text}
            onChange={(e) => setText(e.target.value)}
            placeholder="Nhập ghi chú bác sĩ..."
            rows={5}
            className="mt-1 block w-full p-3 border border-gray-300 rounded-md shadow-sm focus:ring-blue-500 focus:border-blue-500"
          />
        </div>
        <button
          type="submit"
          disabled={loading}
          className={`w-full py-3 px-4 bg-blue-600 text-white font-semibold rounded-md shadow-sm hover:bg-blue-700 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:ring-offset-2 ${loading ? 'opacity-50 cursor-not-allowed' : ''}`}
        >
          {loading ? 'Đang xử lý...' : 'Phân tích'}
        </button>
      </form>

      {error && (
        <p className="text-red-600 font-medium text-center">{error}</p>
      )}
      {result && (
        <div className="p-4 bg-gray-50 rounded-md shadow-sm space-y-4">
          <div>
            <h3 className="text-lg font-semibold text-blue-600">Tóm tắt:</h3>
            <p className="mt-1 text-gray-800">{result.summary}</p>
          </div>
          <div>
            <h3 className="text-lg font-semibold text-blue-600">Mức độ nghiêm trọng:</h3>
            <p
              className={`mt-1 font-medium ${result.severity === 'Nhẹ' ? 'text-green-600' :
                result.severity === 'Trung bình' ? 'text-yellow-600' :
                  'text-red-600'
                }`}
            >
              {result.severity}
            </p>
          </div>
          <div>
            <h3 className="text-lg font-semibold text-blue-600">Gợi ý điều trị:</h3>
            <p className="mt-1 text-gray-800">{result.treatment}</p>
          </div>
          {result.similar_notes && result.similar_notes.length > 0 && (
            <div>
              <h3 className="text-lg font-semibold text-blue-600">Các trường hợp tương tự:</h3>
              <div className="mt-2 space-y-2">
                {result.similar_notes.map((note, index) => (
                  <div key={index} className="border rounded-md">
                    <button
                      onClick={() => toggleNote(index)}
                      className="w-full text-left p-2 bg-gray-100 hover:bg-gray-200 rounded-t-md"
                    >
                      Trường hợp {index + 1} (Độ tương đồng: {note.score.toFixed(2)})
                    </button>
                    {expandedNotes[index] && (
                      <div className="p-2 bg-white rounded-b-md">
                        <p className="text-gray-700"><strong>Ghi chú:</strong> {note.text}</p>
                        <p className="text-gray-600"><strong>Tóm tắt:</strong> {note.summary}</p>
                        <p className="text-gray-600"><strong>Điều trị:</strong> {note.treatment}</p>
                      </div>
                    )}
                  </div>
                ))}
              </div>
            </div>
          )}
        </div>
      )}
    </div>
  );
}

export default NoteAnalyzer;