import React, { useState } from 'react';
import { Sparkles, ChevronDown, ChevronUp, Loader2 } from 'lucide-react';
import { explainDoc } from '../api';
import ReactMarkdown from 'react-markdown';

const AISummary = ({ docId, content }) => {
  const [summary, setSummary] = useState(null);
  const [loading, setLoading] = useState(false);
  const [expanded, setExpanded] = useState(true);
  const [error, setError] = useState(null);

  const handleGenerateSummary = async () => {
    setLoading(true);
    setError(null);
    try {
      // 截取前 3000 字符避免 token 溢出，实际应由后端处理
      const textToExplain = content.substring(0, 3000);
      const res = await explainDoc(textToExplain);
      setSummary(res.data.explanation);
    } catch (err) {
      setError("生成摘要失败，请稍后重试");
    } finally {
      setLoading(false);
    }
  };

  if (!summary && !loading && !error) {
    return (
      <button
        onClick={handleGenerateSummary}
        className="flex items-center gap-2 px-3 py-1.5 text-sm font-medium text-indigo-600 bg-indigo-50 hover:bg-indigo-100 rounded-full transition-colors border border-indigo-200"
      >
        <Sparkles className="w-4 h-4" />
        AI 总结
      </button>
    );
  }

  return (
    <div className="mb-6 rounded-xl border border-indigo-100 bg-gradient-to-br from-indigo-50/50 to-white shadow-sm overflow-hidden">
      <div 
        className="flex items-center justify-between px-4 py-3 bg-indigo-50/30 cursor-pointer select-none"
        onClick={() => setExpanded(!expanded)}
      >
        <div className="flex items-center gap-2 text-indigo-700 font-medium">
          <Sparkles className="w-4 h-4" />
          <span>AI 智能摘要</span>
        </div>
        <button className="text-indigo-400 hover:text-indigo-600">
          {expanded ? <ChevronUp className="w-4 h-4" /> : <ChevronDown className="w-4 h-4" />}
        </button>
      </div>
      
      {expanded && (
        <div className="px-4 py-3 text-sm text-gray-700 leading-relaxed border-t border-indigo-50">
          {loading ? (
            <div className="flex items-center gap-3 py-2 text-indigo-500">
              <Loader2 className="w-5 h-5 animate-spin" />
              <span>正在分析文档内容...</span>
            </div>
          ) : error ? (
            <div className="text-red-500 py-2">{error}</div>
          ) : (
            <div className="prose prose-sm max-w-none prose-indigo">
              <ReactMarkdown>{summary}</ReactMarkdown>
            </div>
          )}
        </div>
      )}
    </div>
  );
};

export default AISummary;
