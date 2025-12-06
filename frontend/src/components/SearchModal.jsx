import React, { useState, useEffect, useRef } from 'react';
import { Search, X, FileText, Loader2 } from 'lucide-react';
import { searchDocs } from '../api';
import { useNavigate } from 'react-router-dom';

const SearchModal = ({ isOpen, onClose }) => {
  const [query, setQuery] = useState('');
  const [results, setResults] = useState([]);
  const [loading, setLoading] = useState(false);
  const inputRef = useRef(null);
  const navigate = useNavigate();

  useEffect(() => {
    if (isOpen && inputRef.current) {
      inputRef.current.focus();
    }
  }, [isOpen]);

  const handleSearch = async (e) => {
    e.preventDefault();
    if (!query.trim()) return;

    setLoading(true);
    try {
      const res = await searchDocs(query);
      setResults(res.data);
    } catch (error) {
      console.error("Search failed", error);
    } finally {
      setLoading(false);
    }
  };

  const handleNavigate = (repo_id, slug) => {
    if (repo_id && slug) {
      navigate(`/repos/${repo_id}/docs/${slug}`);
      onClose();
    }
  };

  if (!isOpen) return null;

  return (
    <div className="fixed inset-0 z-50 flex items-start justify-center pt-20 bg-black/50 backdrop-blur-sm" onClick={onClose}>
      <div 
        className="w-full max-w-2xl bg-white rounded-xl shadow-2xl overflow-hidden mx-4 animate-in fade-in zoom-in duration-200"
        onClick={e => e.stopPropagation()}
      >
        {/* Search Header */}
        <div className="flex items-center border-b border-gray-100 p-4">
          <Search className="w-5 h-5 text-gray-400 mr-3" />
          <form onSubmit={handleSearch} className="flex-1">
            <input
              ref={inputRef}
              type="text"
              className="w-full outline-none text-lg text-gray-700 placeholder-gray-400"
              placeholder="搜索文档或提问..."
              value={query}
              onChange={(e) => setQuery(e.target.value)}
            />
          </form>
          <button onClick={onClose} className="p-1 hover:bg-gray-100 rounded-full transition-colors">
            <X className="w-5 h-5 text-gray-500" />
          </button>
        </div>

        {/* Results Area */}
        <div className="max-h-[60vh] overflow-y-auto bg-gray-50/50">
          {loading ? (
            <div className="flex flex-col items-center justify-center py-12 text-gray-500">
              <Loader2 className="w-8 h-8 animate-spin mb-2 text-blue-500" />
              <p>正在搜索知识库...</p>
            </div>
          ) : results.length > 0 ? (
            <div className="p-2">
              <h3 className="text-xs font-semibold text-gray-400 uppercase tracking-wider px-3 py-2">
                语义搜索结果
              </h3>
              {results.map((doc) => (
                <div 
                  key={doc.id || doc.slug}
                  onClick={() => handleNavigate(doc.repo_id, doc.slug)}
                  className="flex items-start p-3 hover:bg-blue-50 rounded-lg cursor-pointer group transition-colors"
                >
                  <div className="mt-1 mr-3 p-2 bg-white rounded-md shadow-sm group-hover:shadow-md transition-shadow">
                    <FileText className="w-5 h-5 text-blue-500" />
                  </div>
                  <div>
                    <h4 className="font-medium text-gray-800 group-hover:text-blue-600 transition-colors">
                      {doc.title}
                    </h4>
                    <p className="text-sm text-gray-500 line-clamp-2 mt-1">
                      {doc.content || doc.description || "暂无预览"}
                    </p>
                  </div>
                </div>
              ))}
            </div>
          ) : query && !loading ? (
            <div className="py-12 text-center text-gray-500">
              <p>未找到相关文档</p>
            </div>
          ) : (
            <div className="py-12 text-center text-gray-400 text-sm">
              输入关键词或问题，按回车搜索
            </div>
          )}
        </div>
        
        {/* Footer */}
        <div className="bg-gray-50 px-4 py-2 border-t border-gray-100 flex justify-between items-center text-xs text-gray-400">
          <span>Powered by RAG & Qdrant</span>
          <div className="flex gap-2">
            <span className="bg-white border border-gray-200 px-1.5 rounded shadow-sm">Esc</span> to close
          </div>
        </div>
      </div>
    </div>
  );
};

export default SearchModal;
