import React from 'react';
import NoteAnalyzer from './components/NoteAnalyzer';

function App() {
  return (
    <div className="min-h-screen bg-gray-100 flex flex-col">
      <header className="bg-blue-600 text-white text-center py-6">
        <h1 className="text-3xl font-bold">Phân tích Ghi chú Bác sĩ</h1>
      </header>
      <main className="flex-grow p-6">
        <div className="grid grid-cols-1 md:grid-cols-3 gap-6 mb-6">
          <div className="bg-white p-4 rounded-lg shadow">
            <h2 className="text-xl font-semibold">Ghi chú hôm nay</h2>
            <p className="text-2xl">5</p> {/* Giả lập */}
          </div>
          <div className="bg-white p-4 rounded-lg shadow">
            <h2 className="text-xl font-semibold">Trường hợp nặng</h2>
            <p className="text-2xl text-red-600">1</p> {/* Giả lập */}
          </div>
          <div className="bg-white p-4 rounded-lg shadow">
            <h2 className="text-xl font-semibold">Tìm kiếm nhanh</h2>
            <input
              className="mt-2 w-full p-2 border rounded"
              placeholder="Tìm ghi chú..."
              onKeyPress={(e) => {
                if (e.key === 'Enter') {
                  window.location.href = `/search?query=${e.target.value}`;
                }
              }}
            />
          </div>
        </div>
        <NoteAnalyzer />
      </main>
    </div>
  );
}

export default App;