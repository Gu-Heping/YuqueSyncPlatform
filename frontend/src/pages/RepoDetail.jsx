import React, { useEffect, useState, useMemo } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { getRepoDocs, getDocDetail } from '../api';
import { ChevronRight, ChevronDown, FileText, Folder, Menu, X } from 'lucide-react';
import DOMPurify from 'dompurify';
import 'github-markdown-css/github-markdown.css';
import AISummary from '../components/AISummary';

const TreeNode = ({ node, onSelect, selectedSlug, level = 0 }) => {
  const [expanded, setExpanded] = useState(false);
  const hasChildren = node.children && node.children.length > 0;
  const isSelected = node.slug === selectedSlug;

  const handleClick = (e) => {
    e.stopPropagation();
    if (hasChildren) {
      setExpanded(!expanded);
    }
    // Only fetch content if it's a DOC type or has a slug (TITLE might not have content)
    if (node.type === 'DOC') {
      onSelect(node);
    }
  };

  return (
    <div className="select-none">
      <div
        className={`flex items-center py-1 px-2 cursor-pointer hover:bg-gray-100 rounded ${
          isSelected ? 'bg-blue-50 text-blue-600' : 'text-gray-700'
        }`}
        style={{ paddingLeft: `${level * 12 + 8}px` }}
        onClick={handleClick}
      >
        <span className="mr-1 text-gray-400">
          {hasChildren ? (
            expanded ? <ChevronDown size={14} /> : <ChevronRight size={14} />
          ) : (
            <span className="w-[14px] inline-block" />
          )}
        </span>
        <span className="mr-2 text-gray-500">
          {node.type === 'TITLE' ? <Folder size={14} /> : <FileText size={14} />}
        </span>
        <span className="truncate text-sm">{node.title}</span>
      </div>
      {hasChildren && expanded && (
        <div>
          {node.children.map((child) => (
            <TreeNode
              key={child.uuid}
              node={child}
              onSelect={onSelect}
              selectedSlug={selectedSlug}
              level={level + 1}
            />
          ))}
        </div>
      )}
    </div>
  );
};

const RepoDetail = () => {
  const { repoId, docSlug } = useParams();
  const navigate = useNavigate();
  const [treeData, setTreeData] = useState([]);
  const [flatDocs, setFlatDocs] = useState([]);
  const [selectedDoc, setSelectedDoc] = useState(null);
  const [loading, setLoading] = useState(true);
  const [contentLoading, setContentLoading] = useState(false);
  const [isSidebarOpen, setIsSidebarOpen] = useState(false);

  useEffect(() => {
    const fetchDocs = async () => {
      try {
        const response = await getRepoDocs(repoId);
        const docs = response.data;
        setFlatDocs(docs);
        const tree = buildTree(docs);
        setTreeData(tree);
      } catch (error) {
        console.error('Failed to fetch docs:', error);
      } finally {
        setLoading(false);
      }
    };
    fetchDocs();
  }, [repoId]);

  // Auto-select doc based on URL slug
  useEffect(() => {
    if (docSlug && flatDocs.length > 0) {
      if (selectedDoc?.slug === docSlug) return;
      
      const targetDoc = flatDocs.find(d => d.slug === docSlug);
      if (targetDoc) {
        fetchDocDetail(targetDoc.slug);
      }
    }
  }, [docSlug, flatDocs]);

  const fetchDocDetail = async (slug) => {
    setContentLoading(true);
    try {
      const response = await getDocDetail(slug);
      setSelectedDoc(response.data);
    } catch (error) {
      console.error('Failed to fetch doc detail:', error);
    } finally {
      setContentLoading(false);
    }
  };

  const buildTree = (docs) => {
    const nodeMap = {};
    const roots = [];

    // Initialize map
    docs.forEach((doc) => {
      nodeMap[doc.uuid] = { ...doc, children: [] };
    });

    // Build hierarchy
    docs.forEach((doc) => {
      const node = nodeMap[doc.uuid];
      if (doc.parent_uuid && nodeMap[doc.parent_uuid]) {
        nodeMap[doc.parent_uuid].children.push(node);
      } else {
        roots.push(node);
      }
    });

    // Simple sort by prev_uuid (Linked List Sort)
    const sortNodes = (nodes) => {
      if (!nodes || nodes.length === 0) return [];
      
      // Map prev_uuid -> node
      const prevMap = {};
      const firstNodes = [];
      
      nodes.forEach(node => {
        if (node.prev_uuid) {
          prevMap[node.prev_uuid] = node;
        }
      });

      // Find nodes that are not anyone's next sibling (or have no prev_uuid in this list)
      // Actually, simpler: find the one with prev_uuid that is NOT in the current list of uuids?
      // Or just find the one with prev_uuid == null (if it's the absolute first).
      // But prev_uuid might point to a node outside this list (if filtered).
      // Let's just sort by 'prev_uuid' existence for now or leave unsorted.
      // A robust sort is complex without guaranteed integrity.
      // Fallback: Sort by id or creation time if needed.
      return nodes; 
    };

    return roots;
  };

  const handleSelectDoc = (node) => {
    if (node.slug === selectedDoc?.slug) return;
    navigate(`/repos/${repoId}/docs/${node.slug}`);
    setIsSidebarOpen(false);
  };

  if (loading) return <div className="text-center py-10">加载目录中...</div>;

  return (
    <div className="flex h-[calc(100vh-8rem)] bg-white rounded-lg shadow overflow-hidden relative">
      {/* Mobile Sidebar Overlay */}
      {isSidebarOpen && (
        <div 
          className="fixed inset-0 bg-black/50 z-40 md:hidden"
          onClick={() => setIsSidebarOpen(false)}
        />
      )}

      {/* Sidebar */}
      <div className={`
        fixed inset-y-0 left-0 z-50 w-80 bg-gray-50 border-r border-gray-200 transform transition-transform duration-300 ease-in-out
        md:relative md:translate-x-0 md:z-0
        ${isSidebarOpen ? 'translate-x-0' : '-translate-x-full'}
      `}>
        <div className="h-full overflow-y-auto p-4">
          <div className="flex items-center justify-between mb-4 px-2">
            <h3 className="font-bold text-gray-700">文档目录</h3>
            <button 
              onClick={() => setIsSidebarOpen(false)}
              className="md:hidden p-1 text-gray-500 hover:bg-gray-200 rounded"
            >
              <X size={20} />
            </button>
          </div>
          {treeData.map((node) => (
            <TreeNode
              key={node.uuid}
              node={node}
              onSelect={handleSelectDoc}
              selectedSlug={selectedDoc?.slug}
            />
          ))}
        </div>
      </div>

      {/* Content */}
      <div className="flex-1 overflow-y-auto p-4 md:p-8 w-full">
        {/* Mobile Menu Button */}
        <div className="md:hidden mb-4">
          <button
            onClick={() => setIsSidebarOpen(true)}
            className="flex items-center text-gray-600 hover:text-blue-600"
          >
            <Menu size={24} className="mr-2" />
            <span className="font-medium">目录</span>
          </button>
        </div>

        {contentLoading ? (
          <div className="text-center text-gray-500 mt-20">加载文档内容...</div>
        ) : selectedDoc ? (
          <div className="max-w-4xl mx-auto">
            <div className="flex items-center justify-between mb-6">
              <h1 className="text-2xl md:text-3xl font-bold text-gray-900">{selectedDoc.title}</h1>
            </div>
            
            {/* AI Summary Component */}
            <AISummary docId={selectedDoc.id} content={selectedDoc.body || selectedDoc.body_html} />

            <div className="flex items-center text-sm text-gray-500 mb-8 pb-4 border-b border-gray-200">
              <span className="mr-4">最后更新: {new Date(selectedDoc.updated_at).toLocaleDateString()}</span>
              <span>字数: {selectedDoc.word_count}</span>
            </div>
            <div 
              className="markdown-body"
              dangerouslySetInnerHTML={{ __html: DOMPurify.sanitize(selectedDoc.body_html) }} 
            />
          </div>
        ) : (
          <div className="flex flex-col items-center justify-center h-full text-gray-400">
            <FileText size={48} className="mb-4 opacity-20" />
            <p>请从左侧选择文档阅读</p>
          </div>
        )}
      </div>
    </div>
  );
};

export default RepoDetail;
