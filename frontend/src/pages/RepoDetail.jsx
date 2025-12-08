import React, { useEffect, useState, useMemo, useRef } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { getRepoDocs, getDocDetail, getMembers, getRepos } from '../api';
import { ChevronRight, ChevronDown, FileText, Folder, Menu, X, Loader2, ExternalLink, List, AlignRight, Pin, PinOff } from 'lucide-react';
import DOMPurify from 'dompurify';
import 'github-markdown-css/github-markdown.css';
import AISummary from '../components/AISummary';
import MemberModal from '../components/MemberModal';
import { formatDate } from '../utils/date';
import hljs from 'highlight.js';
import 'highlight.js/styles/github.css';

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
        className={`flex items-center py-1.5 px-2 cursor-pointer hover:bg-gray-100 dark:hover:bg-gray-700 rounded transition-colors ${
          isSelected ? 'bg-blue-50 dark:bg-blue-900/30 text-blue-600 dark:text-blue-400' : 'text-gray-700 dark:text-gray-300'
        }`}
        style={{ paddingLeft: `${level * 12 + 8}px` }}
        onClick={handleClick}
      >
        <span className="mr-1 text-gray-400 dark:text-gray-500">
          {hasChildren ? (
            expanded ? <ChevronDown size={14} /> : <ChevronRight size={14} />
          ) : (
            <span className="w-[14px] inline-block" />
          )}
        </span>
        <span className="mr-2 text-gray-500 dark:text-gray-400">
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

const TableOfContents = ({ toc, activeId, onSelect }) => {
  if (!toc || toc.length === 0) return null;

  return (
    <div className="h-full overflow-y-auto">
      <ul className="space-y-1 text-sm">
        {toc.map((item) => (
          <li 
            key={item.id}
            className={`
              pl-2 border-l-2 transition-colors cursor-pointer py-1
              ${activeId === item.id 
                ? 'border-blue-500 text-blue-600 dark:text-blue-400 font-medium bg-blue-50 dark:bg-blue-900/20' 
                : 'border-transparent text-gray-500 dark:text-gray-400 hover:text-gray-900 dark:hover:text-gray-200 hover:border-gray-300'}
            `}
            style={{ marginLeft: `${(item.level - 1) * 12}px` }}
            onClick={() => onSelect(item.id)}
          >
            <a href={`#${item.id}`} onClick={(e) => e.preventDefault()} className="block truncate">
              {item.text}
            </a>
          </li>
        ))}
      </ul>
    </div>
  );
};

const RepoDetail = () => {
  const { repoId, docSlug } = useParams();
  const navigate = useNavigate();
  const [treeData, setTreeData] = useState([]);
  const [flatDocs, setFlatDocs] = useState([]);
  const [selectedDoc, setSelectedDoc] = useState(null);
  const markdownRef = useRef(null);

  useEffect(() => {
    if (selectedDoc && markdownRef.current) {
      const blocks = markdownRef.current.querySelectorAll('pre code');
      blocks.forEach((block) => {
        hljs.highlightElement(block);
      });
    }
  }, [selectedDoc]);
  const [loading, setLoading] = useState(true);
  const [contentLoading, setContentLoading] = useState(false);
  const [isSidebarOpen, setIsSidebarOpen] = useState(false);
  const [members, setMembers] = useState([]);
  const [selectedMember, setSelectedMember] = useState(null);
  const [repoInfo, setRepoInfo] = useState(null);
  
  // Sidebar Pin State
  const [leftPinned, setLeftPinned] = useState(true);
  const [rightPinned, setRightPinned] = useState(true);
  const [leftHovered, setLeftHovered] = useState(false);
  const [rightHovered, setRightHovered] = useState(false);

  // TOC State
  const [toc, setToc] = useState([]);
  const [activeId, setActiveId] = useState('');
  const [isTocOpen, setIsTocOpen] = useState(false);

  useEffect(() => {
    const fetchRepoInfo = async () => {
      try {
        const response = await getRepos();
        const currentRepo = response.data.find(r => r.yuque_id.toString() === repoId);
        setRepoInfo(currentRepo);
      } catch (error) {
        console.error('Failed to fetch repo info:', error);
      }
    };
    fetchRepoInfo();
  }, [repoId]);

  useEffect(() => {
    const fetchMembers = async () => {
      try {
        const response = await getMembers();
        setMembers(response.data);
      } catch (error) {
        console.error('Failed to fetch members:', error);
      }
    };
    fetchMembers();
  }, []);

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

  // Parse TOC from content
  useEffect(() => {
    if (!selectedDoc) return;
    
    // Wait for DOM to update
    const timer = setTimeout(() => {
      const content = document.querySelector('.markdown-body');
      if (!content) return;
      
      const headers = content.querySelectorAll('h1, h2, h3, h4, h5, h6');
      const tocData = Array.from(headers)
        .filter(header => {
          // Ignore headers inside details tags unless they are in the summary
          const inDetails = header.closest('details');
          const inSummary = header.closest('summary');
          if (inDetails && !inSummary) return false;
          
          // Ignore empty headers
          return header.innerText.trim().length > 0;
        })
        .map((header, index) => {
        const id = header.id || `heading-${index}`;
        header.id = id; // Ensure ID exists
        return {
          id,
          text: header.innerText,
          level: parseInt(header.tagName.substring(1)),
        };
      });
      setToc(tocData);
    }, 100);

    return () => clearTimeout(timer);
  }, [selectedDoc]);

  // Scroll Spy
  useEffect(() => {
    const observer = new IntersectionObserver(
      (entries) => {
        entries.forEach((entry) => {
          if (entry.isIntersecting) {
            setActiveId(entry.target.id);
          }
        });
      },
      { rootMargin: '0px 0px -80% 0px' }
    );

    const headers = document.querySelectorAll('.markdown-body h1, .markdown-body h2, .markdown-body h3, .markdown-body h4, .markdown-body h5, .markdown-body h6');
    headers.forEach((header) => observer.observe(header));

    return () => observer.disconnect();
  }, [toc]);

  const scrollToHeading = (id) => {
    const element = document.getElementById(id);
    if (element) {
      element.scrollIntoView({ behavior: 'smooth' });
      setActiveId(id);
      setIsTocOpen(false); // Close mobile TOC if open
    }
  };

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
      return nodes; 
    };

    return roots;
  };

  const author = useMemo(() => {
    if (!selectedDoc || !members.length) return null;
    return members.find(m => m.yuque_id === selectedDoc.user_id);
  }, [selectedDoc, members]);

  const handleSelectDoc = (node) => {
    if (node.slug === selectedDoc?.slug) return;
    navigate(`/repos/${repoId}/docs/${node.slug}`);
    setIsSidebarOpen(false);
  };

  const handleMemberUpdate = (updatedMember) => {
    setMembers(prev => prev.map(m => m.yuque_id === updatedMember.yuque_id ? updatedMember : m));
    if (selectedMember && selectedMember.yuque_id === updatedMember.yuque_id) {
      setSelectedMember(updatedMember);
    }
  };

  if (loading) return (
    <div className="flex justify-center items-center h-[calc(100vh-8rem)]">
      <Loader2 className="w-8 h-8 animate-spin text-blue-500" />
    </div>
  );

  return (
    <div className="flex h-[calc(100vh-8rem)] bg-white dark:bg-gray-800 rounded-lg shadow overflow-hidden relative border border-gray-200 dark:border-gray-700">
      {/* Mobile Sidebar Overlay */}
      {isSidebarOpen && (
        <div 
          className="fixed inset-0 bg-black/50 z-40 md:hidden"
          onClick={() => setIsSidebarOpen(false)}
        />
      )}

      {/* Mobile TOC Overlay */}
      {isTocOpen && (
        <div 
          className="fixed inset-0 bg-black/50 z-40 xl:hidden"
          onClick={() => setIsTocOpen(false)}
        />
      )}

      {/* Mobile Sidebar (Doc Tree) */}
      <div className={`
        fixed inset-y-0 left-0 z-50 w-80 bg-gray-50 dark:bg-gray-900 border-r border-gray-200 dark:border-gray-700 transform transition-transform duration-300 ease-in-out md:hidden
        ${isSidebarOpen ? 'translate-x-0' : '-translate-x-full'}
      `}>
        <div className="h-full overflow-y-auto p-4">
          <div className="flex items-center justify-between mb-4 px-2">
            <h3 className="font-bold text-gray-700 dark:text-gray-200">文档目录</h3>
            <button 
              onClick={() => setIsSidebarOpen(false)}
              className="p-1 text-gray-500 hover:bg-gray-200 dark:hover:bg-gray-700 rounded"
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

      {/* Desktop Left Sidebar */}
      <div 
        className={`hidden md:block relative z-20 transition-all duration-300 ${leftPinned ? 'w-80' : 'w-8'}`}
        onMouseEnter={() => setLeftHovered(true)}
        onMouseLeave={() => setLeftHovered(false)}
      >
        <div className={`
          h-full bg-gray-50 dark:bg-gray-900 border-r border-gray-200 dark:border-gray-700
          transition-transform duration-300 ease-in-out
          absolute top-0 left-0 w-80 shadow-xl
          ${leftPinned ? 'translate-x-0' : (leftHovered ? 'translate-x-0' : '-translate-x-[calc(100%-2rem)]')}
        `}>
          <div className="h-full flex flex-col">
            <div className="flex items-center justify-between px-2 border-b border-gray-200 dark:border-gray-700 shrink-0 h-14">
              <h3 className={`font-bold text-gray-700 dark:text-gray-200 transition-opacity duration-200 ${!leftPinned && !leftHovered ? 'opacity-0' : 'opacity-100'}`}>
                文档目录
              </h3>
              <button 
                onClick={() => setLeftPinned(!leftPinned)}
                className="p-1 text-gray-500 hover:bg-gray-200 dark:hover:bg-gray-700 rounded"
                title={leftPinned ? "取消固定" : "固定侧边栏"}
              >
                {leftPinned ? <PinOff size={16} /> : <Pin size={16} className="fill-current" />}
              </button>
            </div>
            <div className={`flex-1 overflow-y-auto p-4 transition-opacity duration-200 ${!leftPinned && !leftHovered ? 'opacity-0' : 'opacity-100'}`}>
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
        </div>
      </div>

      {/* Main Content Area Wrapper */}
      <div className="flex-1 flex min-w-0 bg-white dark:bg-gray-800 relative">
        
        {/* Article Content (Scrollable) */}
        <div className="flex-1 overflow-y-auto p-4 md:p-8 scroll-smooth" id="article-scroll-container">
          {/* Mobile Menu Button */}
          <div className="md:hidden mb-4 flex justify-between items-center">
            <button
              onClick={() => setIsSidebarOpen(true)}
              className="flex items-center text-gray-600 dark:text-gray-300 hover:text-blue-600 dark:hover:text-blue-400"
            >
              <Menu size={24} className="mr-2" />
              <span className="font-medium">目录</span>
            </button>
            {toc.length > 0 && (
              <button
                onClick={() => setIsTocOpen(true)}
                className="flex items-center text-gray-600 dark:text-gray-300 hover:text-blue-600 dark:hover:text-blue-400"
              >
                <List size={24} />
              </button>
            )}
          </div>

          {contentLoading ? (
            <div className="flex justify-center items-center h-64">
              <Loader2 className="w-8 h-8 animate-spin text-blue-500" />
            </div>
          ) : selectedDoc ? (
            <div className="max-w-3xl mx-auto">
              <div className="flex items-center justify-between mb-6">
                <h1 className="text-2xl md:text-3xl font-bold text-gray-900 dark:text-white">{selectedDoc.title}</h1>
              </div>
              
              <div className="flex flex-wrap items-center text-sm text-gray-500 dark:text-gray-400 mb-8 pb-4 border-b border-gray-200 dark:border-gray-700 gap-y-2">
                <span className="mr-4 flex items-center">
                  作者: 
                  <button 
                    onClick={() => author && setSelectedMember(author)}
                    className={`ml-1 font-medium ${author ? 'text-blue-600 dark:text-blue-400 hover:underline cursor-pointer' : ''}`}
                    disabled={!author}
                  >
                    {author ? author.name : '未知作者'}
                  </button>
                </span>
                <span className="mr-4">
                  更新: {formatDate(selectedDoc.content_updated_at || selectedDoc.updated_at, { hour: '2-digit', minute: '2-digit' })}
                </span>
                <span className="mr-4">字数: {selectedDoc.word_count}</span>
                <span className="mr-4">阅读: {selectedDoc.read_count || 0}</span>
                <span>点赞: {selectedDoc.likes_count || 0}</span>
              </div>

              {/* AI Summary Component */}
              <div className="mb-6">
                <AISummary docId={selectedDoc.id} content={selectedDoc.body || selectedDoc.body_html} />
              </div>
              
              <div 
                ref={markdownRef}
                className="markdown-body dark:bg-gray-800 dark:text-gray-200"
                dangerouslySetInnerHTML={{ __html: DOMPurify.sanitize(selectedDoc.body_html) }} 
              />
              
              {repoInfo && (
                <div className="mt-8 pt-4 border-t border-gray-200 dark:border-gray-700">
                  <a 
                    href={`https://nova.yuque.com/${repoInfo.namespace}/${selectedDoc.slug}`}
                    target="_blank"
                    rel="noopener noreferrer"
                    className="text-blue-600 dark:text-blue-400 hover:underline flex items-center w-fit"
                  >
                    <ExternalLink className="w-4 h-4 mr-1" />
                    查看原文
                  </a>
                </div>
              )}

              {/* Add custom styles for dark mode markdown if github-markdown-css doesn't support it automatically via class */}
              <style>{`
                .dark .markdown-body {
                  color-scheme: dark;
                  color: #c9d1d9;
                  background-color: #1f2937; /* gray-800 */
                  
                  /* GitHub Dark Dimmed Variables for Syntax Highlighting */
                  --color-prettylights-syntax-comment: #8b949e;
                  --color-prettylights-syntax-constant: #79c0ff;
                  --color-prettylights-syntax-entity: #d2a8ff;
                  --color-prettylights-syntax-storage-modifier-import: #c9d1d9;
                  --color-prettylights-syntax-entity-tag: #7ee787;
                  --color-prettylights-syntax-keyword: #ff7b72;
                  --color-prettylights-syntax-string: #a5d6ff;
                  --color-prettylights-syntax-variable: #ffa657;
                  --color-prettylights-syntax-brackethighlighter-unmatched: #f85149;
                  --color-prettylights-syntax-invalid-illegal-text: #f0f6fc;
                  --color-prettylights-syntax-invalid-illegal-bg: #8e1519;
                  --color-prettylights-syntax-carriage-return-text: #f0f6fc;
                  --color-prettylights-syntax-carriage-return-bg: #b62324;
                  --color-prettylights-syntax-string-regexp: #7ee787;
                  --color-prettylights-syntax-markup-list: #f2cc60;
                  --color-prettylights-syntax-markup-heading: #1f6feb;
                  --color-prettylights-syntax-markup-italic: #c9d1d9;
                  --color-prettylights-syntax-markup-bold: #c9d1d9;
                  --color-prettylights-syntax-markup-deleted-text: #ffdcd7;
                  --color-prettylights-syntax-markup-deleted-bg: #67060c;
                  --color-prettylights-syntax-markup-inserted-text: #aff5b4;
                  --color-prettylights-syntax-markup-inserted-bg: #033a16;
                  --color-prettylights-syntax-markup-changed-text: #ffdfb6;
                  --color-prettylights-syntax-markup-changed-bg: #5a1e02;
                  --color-prettylights-syntax-markup-ignored-text: #c9d1d9;
                  --color-prettylights-syntax-markup-ignored-bg: #1158c7;
                  --color-prettylights-syntax-meta-diff-range: #d2a8ff;
                  --color-prettylights-syntax-brackethighlighter-angle: #8b949e;
                  --color-prettylights-syntax-sublimelinter-gutter-mark: #484f58;
                  --color-prettylights-syntax-constant-other-reference-link: #a5d6ff;
                }
                
                /* Override highlight.js styles for dark mode */
                .dark .hljs {
                  color: #c9d1d9;
                  background: #161b22;
                }
                .dark .hljs-doctag,
                .dark .hljs-keyword,
                .dark .hljs-meta .hljs-keyword,
                .dark .hljs-template-tag,
                .dark .hljs-template-variable,
                .dark .hljs-type,
                .dark .hljs-variable.language_ {
                  color: #ff7b72;
                }
                .dark .hljs-title,
                .dark .hljs-title.class_,
                .dark .hljs-title.class_.inherited__,
                .dark .hljs-title.function_ {
                  color: #d2a8ff;
                }
                .dark .hljs-attr,
                .dark .hljs-attribute,
                .dark .hljs-literal,
                .dark .hljs-meta,
                .dark .hljs-number,
                .dark .hljs-operator,
                .dark .hljs-variable,
                .dark .hljs-selector-attr,
                .dark .hljs-selector-class,
                .dark .hljs-selector-id {
                  color: #79c0ff;
                }
                .dark .hljs-regexp,
                .dark .hljs-string,
                .dark .hljs-meta .hljs-string {
                  color: #a5d6ff;
                }
                .dark .hljs-built_in,
                .dark .hljs-symbol {
                  color: #ffa657;
                }
                .dark .hljs-comment,
                .dark .hljs-code,
                .dark .hljs-formula {
                  color: #8b949e;
                }
                .dark .hljs-name,
                .dark .hljs-quote,
                .dark .hljs-selector-tag,
                .dark .hljs-selector-pseudo {
                  color: #7ee787;
                }
                .dark .hljs-subst {
                  color: #c9d1d9;
                }
                .dark .hljs-section {
                  color: #1f6feb;
                  font-weight: bold;
                }
                .dark .hljs-bullet {
                  color: #f2cc60;
                }
                .dark .hljs-emphasis {
                  color: #c9d1d9;
                  font-style: italic;
                }
                .dark .hljs-strong {
                  color: #c9d1d9;
                  font-weight: bold;
                }
                .dark .hljs-addition {
                  color: #aff5b4;
                  background-color: #033a16;
                }
                .dark .hljs-deletion {
                  color: #ffdcd7;
                  background-color: #67060c;
                }

                .dark .markdown-body a {
                  color: #58a6ff;
                }
                .dark .markdown-body pre {
                  background-color: #161b22;
                  border: 1px solid #30363d;
                }
                .dark .markdown-body code {
                  color: #c9d1d9;
                  background-color: rgba(110, 118, 129, 0.4);
                }
                .dark .markdown-body pre code {
                  color: #c9d1d9;
                  background-color: transparent;
                }
                .dark .markdown-body blockquote {
                  color: #8b949e;
                  border-left-color: #30363d;
                }
                .dark .markdown-body table tr {
                  background-color: #1f2937;
                  border-top-color: #30363d;
                }
                .dark .markdown-body table tr:nth-child(2n) {
                  background-color: #161b22;
                }
                .dark .markdown-body table th,
                .dark .markdown-body table td {
                  border-color: #30363d;
                }
              `}</style>
            </div>
          ) : (
            <div className="flex flex-col items-center justify-center h-full text-gray-400 dark:text-gray-600">
              <FileText size={48} className="mb-4 opacity-20" />
              <p>请从左侧选择文档阅读</p>
            </div>
          )}
        </div>

        {/* Desktop TOC (Right Sidebar) */}
        {selectedDoc && toc.length > 0 && (
          <div 
            className={`hidden xl:block relative z-20 transition-all duration-300 ${rightPinned ? 'w-64' : 'w-8'}`}
            onMouseEnter={() => setRightHovered(true)}
            onMouseLeave={() => setRightHovered(false)}
          >
            <div className={`
              h-full bg-gray-50/50 dark:bg-gray-900/50 border-l border-gray-200 dark:border-gray-700
              transition-transform duration-300 ease-in-out
              absolute top-0 right-0 w-64 shadow-xl
              ${rightPinned ? 'translate-x-0' : (rightHovered ? 'translate-x-0' : 'translate-x-[calc(100%-2rem)]')}
            `}>
              <div className="h-full flex flex-col">
                <div className="flex items-center justify-between px-2 shrink-0 h-14">
                  <button 
                    onClick={() => setRightPinned(!rightPinned)}
                    className="p-1 text-gray-500 hover:bg-gray-200 dark:hover:bg-gray-700 rounded"
                    title={rightPinned ? "取消固定" : "固定侧边栏"}
                  >
                    {rightPinned ? <PinOff size={16} /> : <Pin size={16} className="fill-current" />}
                  </button>
                  <span className={`font-bold text-gray-700 dark:text-gray-200 transition-opacity duration-200 ${!rightPinned && !rightHovered ? 'opacity-0' : 'opacity-100'}`}>
                    本文目录
                  </span>
                </div>
                <div className={`flex-1 overflow-y-auto p-4 pt-0 transition-opacity duration-200 ${!rightPinned && !rightHovered ? 'opacity-0' : 'opacity-100'}`}>
                  <TableOfContents toc={toc} activeId={activeId} onSelect={scrollToHeading} />
                </div>
              </div>
            </div>
          </div>
        )}

        {/* Mobile TOC Drawer (Right Slide-in) */}
        <div className={`
          fixed inset-y-0 right-0 z-50 w-72 bg-white dark:bg-gray-800 border-l border-gray-200 dark:border-gray-700 transform transition-transform duration-300 ease-in-out xl:hidden
          ${isTocOpen ? 'translate-x-0' : 'translate-x-full'}
        `}>
          <div className="h-full overflow-y-auto p-4">
            <div className="flex items-center justify-between mb-4">
              <h3 className="font-bold text-gray-700 dark:text-gray-200">内容大纲</h3>
              <button 
                onClick={() => setIsTocOpen(false)}
                className="p-1 text-gray-500 hover:bg-gray-200 dark:hover:bg-gray-700 rounded"
              >
                <X size={20} />
              </button>
            </div>
            <TableOfContents toc={toc} activeId={activeId} onSelect={scrollToHeading} />
          </div>
        </div>

        {/* Mobile Floating TOC Button (Bottom Right) */}
        {selectedDoc && toc.length > 0 && !isTocOpen && (
          <button
            onClick={() => setIsTocOpen(true)}
            className="fixed bottom-24 right-6 z-40 p-3 bg-white dark:bg-gray-800 text-gray-600 dark:text-gray-300 rounded-full shadow-lg border border-gray-200 dark:border-gray-700 xl:hidden hover:bg-gray-50 dark:hover:bg-gray-700 transition-all"
            aria-label="Toggle Table of Contents"
          >
            <List size={20} />
          </button>
        )}

      </div>

      {/* Member Modal */}
      {selectedMember && (
        <MemberModal 
          member={selectedMember} 
          onClose={() => setSelectedMember(null)} 
          onUpdate={handleMemberUpdate}
        />
      )}
    </div>
  );
};

export default RepoDetail;