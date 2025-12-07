import os
import re
import asyncio
# 强制禁用本地连接的代理，防止 502 Bad Gateway
os.environ["NO_PROXY"] = "localhost,127.0.0.1"

import logging
from typing import List, Optional
from bs4 import BeautifulSoup
from qdrant_client import QdrantClient, models
from langchain_qdrant import QdrantVectorStore
from langchain_openai import OpenAIEmbeddings, ChatOpenAI
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_core.documents import Document
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser
from langchain_core.messages import HumanMessage, AIMessage

from app.core.config import settings
from app.models.schemas import Doc, ChatSession, ChatMessage, Member, User
from beanie.operators import In

logger = logging.getLogger(__name__)

class RAGService:
    """
    RAG 服务：负责文档向量化、存储、检索和问答
    """
    def __init__(self):
        # 1. 初始化 Embedding 模型
        self.embeddings = OpenAIEmbeddings(
            api_key=settings.OPENAI_API_KEY,
            base_url=settings.OPENAI_BASE_URL,
            model="text-embedding-3-small" # 或其他兼容模型
        )
        
        # 2. 初始化 LLM
        self.llm = ChatOpenAI(
            api_key=settings.OPENAI_API_KEY,
            base_url=settings.OPENAI_BASE_URL,
            model="gpt-4o", # 或 gpt-3.5-turbo
            temperature=0.3
        )

        # 3. 初始化 Qdrant 客户端和 VectorStore
        print(f"Connecting to Qdrant at: {settings.QDRANT_URL}")
        self.client = QdrantClient(url=settings.QDRANT_URL)
        self.collection_name = settings.QDRANT_COLLECTION_NAME
        
        # 检查并创建集合 (如果不存在)
        if not self.client.collection_exists(self.collection_name):
            print(f"Collection '{self.collection_name}' does not exist. Creating it...")
            self.client.create_collection(
                collection_name=self.collection_name,
                vectors_config=models.VectorParams(
                    size=1536,  # text-embedding-3-small 的维度
                    distance=models.Distance.COSINE
                )
            )
            print(f"Collection '{self.collection_name}' created successfully.")

        # 使用 LangChain 的 VectorStore 抽象
        self.vector_store = QdrantVectorStore(
            client=self.client,
            collection_name=self.collection_name,
            embedding=self.embeddings,
        )

    async def upsert_doc_to_vector_db(self, doc: Doc):
        """
        将文档切分并存入向量库 (Data Enrichment)
        """
        if not doc.body:
            return

        try:
            # Clean HTML tags
            soup = BeautifulSoup(doc.body, "html.parser")
            clean_text = soup.get_text(separator="\n")

            # 1. 文本切分
            text_splitter = RecursiveCharacterTextSplitter(
                chunk_size=1000,
                chunk_overlap=200,
                separators=["\n\n", "\n", "。", "！", "？", " ", ""]
            )
            
            # Data Enrichment: 获取作者名
            author_name = "未知用户"
            if doc.user_id:
                member = await Member.find_one(Member.yuque_id == doc.user_id)
                if member:
                    author_name = member.name
                else:
                    user = await User.find_one(User.yuque_id == doc.user_id)
                    if user:
                        author_name = user.name
            
            # Data Enrichment: 格式化日期
            updated_date = "未知日期"
            if doc.updated_at:
                updated_date = doc.updated_at.strftime("%Y-%m-%d")
            elif doc.created_at:
                updated_date = doc.created_at.strftime("%Y-%m-%d")

            # 组合 metadata
            metadata = {
                "doc_id": doc.yuque_id,
                "title": doc.title,
                "slug": doc.slug,
                "repo_id": doc.repo_id,
                "user_id": doc.user_id,
                "author_name": author_name,
                "updated_date": updated_date,
                "source": doc.slug
            }
            
            # 创建 Langchain Documents
            full_text = f"# {doc.title}\n\n{clean_text}"
            chunks = text_splitter.create_documents([full_text], metadatas=[metadata])
            
            if not chunks:
                return

            # 2. 使用 VectorStore 添加文档
            # LangChain 会自动处理 embedding 和 upsert
            self.vector_store.add_documents(chunks)
            
            logger.info(f"Upserted {len(chunks)} chunks for doc {doc.title} ({doc.yuque_id})")

        except Exception as e:
            logger.error(f"Failed to upsert doc {doc.yuque_id} to vector db: {e}")

    async def delete_doc(self, doc_id: int):
        """
        从向量库中删除指定文档的所有切片
        """
        try:
            self.client.delete(
                collection_name=self.collection_name,
                points_selector=models.FilterSelector(
                    filter=models.Filter(
                        must=[
                            models.FieldCondition(
                                key="metadata.doc_id",
                                match=models.MatchValue(value=doc_id),
                            ),
                        ],
                    )
                ),
            )
            logger.info(f"Deleted vectors for doc_id: {doc_id}")
        except Exception as e:
            logger.error(f"Failed to delete vectors for doc_id {doc_id}: {e}")

    def _highlight_text(self, text: str, query: str, window_size: int = 200) -> str:
        """
        简单的关键词高亮和摘要提取
        """
        if not text:
            return ""
            
        # 1. 提取关键词 (简单按空格分词)
        keywords = [k for k in query.split() if k.strip()]
        if not keywords:
            return text[:window_size] + "..."

        # 2. 找到第一个关键词的位置
        lower_text = text.lower()
        first_pos = -1
        for k in keywords:
            pos = lower_text.find(k.lower())
            if pos != -1:
                if first_pos == -1 or pos < first_pos:
                    first_pos = pos
        
        # 3. 截取窗口
        if first_pos == -1:
            start = 0
        else:
            start = max(0, first_pos - 20) # 往前多取一点上下文
        
        end = min(len(text), start + window_size)
        snippet = text[start:end]
        
        # 4. 高亮关键词 (使用正则忽略大小写替换)
        for k in keywords:
            # 使用 re.escape 防止关键词包含正则特殊字符
            pattern = re.compile(re.escape(k), re.IGNORECASE)
            snippet = pattern.sub(lambda m: f"<mark>{m.group(0)}</mark>", snippet)
            
        if start > 0:
            snippet = "..." + snippet
        if end < len(text):
            snippet = snippet + "..."
            
        return snippet

    async def search(self, query: str, limit: int = 20, repo_id: Optional[int] = None):
        """
        混合检索 (Hybrid Search): Keyword (MongoDB) + Vector (Qdrant) + RRF Fusion
        """
        # 为了提高 RRF 融合的效果，内部召回更多的候选文档 (例如 2 倍 limit)
        candidate_limit = max(limit * 2, 50)

        # 1. 定义两路搜索函数
        async def keyword_search():
            try:
                # 构造 MongoDB 文本搜索查询
                find_query = {"$text": {"$search": query}}
                if repo_id:
                    find_query["repo_id"] = repo_id
                
                # 获取候选结果
                return await Doc.find(find_query).limit(candidate_limit).to_list()
            except Exception as e:
                logger.warning(f"Keyword search failed (possibly no index): {e}")
                return []

        async def vector_search():
            try:
                # 构造 Qdrant 过滤条件 (如果需要)
                # filter_dict = {"repo_id": repo_id} if repo_id else {}
                
                # 使用异步向量搜索
                return await self.vector_store.asimilarity_search_with_score(query, k=candidate_limit)
            except Exception as e:
                logger.error(f"Vector search failed: {e}")
                return []

        # 2. 并行执行两路搜索
        keyword_results, vector_results = await asyncio.gather(keyword_search(), vector_search())

        # 3. RRF 融合 (Reciprocal Rank Fusion)
        # score = 1 / (rank + k), k usually 60
        k = 60
        fused_scores = {}
        doc_info_map = {} 

        # 处理 Keyword 结果 (MongoDB Doc)
        for rank, doc in enumerate(keyword_results):
            if not doc.yuque_id: continue
            
            # 提取纯文本用于生成摘要
            text_content = doc.description or ""
            if not text_content and doc.body:
                try:
                    # 尝试去除 HTML 标签 (针对 Lake/HTML 格式)
                    soup = BeautifulSoup(doc.body, "html.parser")
                    text_content = soup.get_text(separator=" ")
                except:
                    text_content = doc.body

            doc_id = doc.yuque_id
            if doc_id not in fused_scores:
                fused_scores[doc_id] = 0
                doc_info_map[doc_id] = {
                    "title": doc.title,
                    "slug": doc.slug,
                    # 使用高亮摘要
                    "content": self._highlight_text(text_content, query),
                    "updated_date": doc.updated_at.strftime("%Y-%m-%d") if doc.updated_at else "",
                    "author_name": "未知作者", # MongoDB Doc 中没有直接存储作者名
                    "source_type": "keyword"
                }
            
            # 给予关键词匹配稍高的权重 (1.5x)
            fused_scores[doc_id] += 1.5 * (1 / (rank + k))

        # 处理 Vector 结果 (LangChain Document)
        for rank, (doc, score) in enumerate(vector_results):
            # 尝试从 metadata 获取 doc_id
            doc_id = doc.metadata.get("doc_id")
            if not doc_id: continue
            
            if doc_id not in fused_scores:
                fused_scores[doc_id] = 0
                doc_info_map[doc_id] = {
                    "title": doc.metadata.get("title"),
                    "slug": doc.metadata.get("slug"),
                    # 对向量检索的片段也进行高亮
                    "content": self._highlight_text(doc.page_content, query),
                    "updated_date": doc.metadata.get("updated_date"),
                    "author_name": doc.metadata.get("author_name"),
                    "source_type": "vector"
                }
            else:
                # 如果已经存在 (即 Keyword 也搜到了)，优先使用 Vector 的 metadata (因为它有 author_name)
                # 并且 content 使用 Vector 的片段可能更相关
                current_info = doc_info_map[doc_id]
                if current_info["source_type"] == "keyword":
                     doc_info_map[doc_id].update({
                        "author_name": doc.metadata.get("author_name"),
                        "content": self._highlight_text(doc.page_content, query),
                        "source_type": "hybrid"
                     })

            fused_scores[doc_id] += 1 / (rank + k)

        # 4. 重新排序
        sorted_ids = sorted(fused_scores.keys(), key=lambda x: fused_scores[x], reverse=True)[:limit]

        # 5. 构造最终结果
        final_results = []
        for doc_id in sorted_ids:
            info = doc_info_map[doc_id]
            final_results.append({
                "score": fused_scores[doc_id],
                **info
            })
            
        return final_results

    async def chat(self, query: str, repo_id: Optional[int] = None, session_id: Optional[str] = None):
        """
        Conversational RAG Pipeline:
        1. Contextualize Query (History-Aware)
        2. Retrieval with Metadata (Parent Document Retrieval)
        3. Answer Generation
        4. Memory Persistence
        """
        # 0. 获取/创建会话
        if not session_id:
            # Create new session
            session = ChatSession(title=query[:50])
            await session.insert()
            session_id = str(session.id)
        
        # 获取历史记录
        history_msgs = await ChatMessage.find(ChatMessage.session_id == session_id).sort("+created_at").to_list()
        chat_history = []
        for msg in history_msgs:
            if msg.role == "user":
                chat_history.append(HumanMessage(content=msg.content))
            else:
                chat_history.append(AIMessage(content=msg.content))

        # Step 1: Contextualize Query (上下文改写)
        final_query = query
        if chat_history:
            contextualize_q_system_prompt = """Given a chat history and the latest user question \
which might reference context in the chat history, formulate a standalone question \
which can be understood without the chat history. Do NOT answer the question, \
just reformulate it if needed and otherwise return it as is."""
            
            contextualize_q_prompt = ChatPromptTemplate.from_messages(
                [
                    ("system", contextualize_q_system_prompt),
                    ("placeholder", "{chat_history}"),
                    ("human", "{input}"),
                ]
            )
            history_chain = contextualize_q_prompt | self.llm | StrOutputParser()
            final_query = await history_chain.ainvoke({
                "chat_history": chat_history,
                "input": query
            })
            logger.info(f"Contextualized query: {final_query}")

        # Step 2: Retrieval (Parent Document Retrieval)
        # 2.1 Vector Search to get candidate chunks
        try:
            # Use async vector search
            vector_results = await self.vector_store.asimilarity_search_with_score(final_query, k=10)
        except Exception as e:
            logger.error(f"Vector search failed in chat: {e}")
            vector_results = []

        # 2.2 Deduplication & ID Extraction
        top_doc_ids = []
        seen_ids = set()
        for doc, score in vector_results:
            # metadata uses 'doc_id' which is yuque_id
            d_id = doc.metadata.get("doc_id")
            if d_id and d_id not in seen_ids:
                top_doc_ids.append(d_id)
                seen_ids.add(d_id)
            if len(top_doc_ids) >= 3:
                break
        
        # 2.3 Full Content Fetching
        docs = []
        if top_doc_ids:
            docs = await Doc.find(In(Doc.yuque_id, top_doc_ids)).to_list()
        
        # Sort docs to match the order of top_doc_ids (relevance)
        docs_map = {d.yuque_id: d for d in docs}
        ordered_docs = []
        for d_id in top_doc_ids:
            if d_id in docs_map:
                ordered_docs.append(docs_map[d_id])

        # 2.4 Context Construction
        context_parts = []
        for d in ordered_docs:
            # Truncate body to 8000 chars to avoid token limit issues
            body = d.body or ""
            if len(body) > 8000:
                body = body[:8000] + "\n...(truncated due to length)..."
            
            # Try to get author name if possible, otherwise use ID
            author_info = f"{d.user_id} (ID)"
            
            part = f"=== Document: {d.title} ===\nAuthor: {author_info}\nUpdate: {d.updated_at}\nContent:\n{body}\n========================="
            context_parts.append(part)
        
        context_text = "\n\n".join(context_parts)
        if not context_text:
            context_text = "No relevant documents found."

        # Step 3: Answer Generation (生成回答)
        qa_system_prompt = """你是一位专业的团队技术顾问。请基于以下检索到的完整文档上下文（Context），回答用户的问题。
这些文档是根据相关性检索到的完整内容，请仔细阅读。
请在回答中尽可能引用文档的标题、作者和最后更新时间，以增加可信度。
如果上下文中没有答案，请诚实地说不知道，不要编造。
回答请使用 Markdown 格式，条理清晰。

上下文内容：
{context}"""
        
        qa_prompt = ChatPromptTemplate.from_messages(
            [
                ("system", qa_system_prompt),
                ("placeholder", "{chat_history}"),
                ("human", "{input}"),
            ]
        )
        
        rag_chain = qa_prompt | self.llm | StrOutputParser()
        
        answer = await rag_chain.ainvoke({
            "context": context_text,
            "chat_history": chat_history,
            "input": final_query 
        })
        
        # Step 4: Memory Persistence (记忆存储)
        # 保存用户提问
        await ChatMessage(session_id=session_id, role="user", content=query).insert()
        
        # 构造 Sources (Simple metadata for UI)
        sources = []
        for d in ordered_docs:
            sources.append({
                "title": d.title,
                "slug": d.slug,
                "yuque_id": d.yuque_id,
                "author_id": d.user_id,
                "updated_at": d.updated_at
            })

        # 保存 AI 回答
        await ChatMessage(session_id=session_id, role="ai", content=answer, sources=sources).insert()
        
        return {
            "answer": answer,
            "sources": sources,
            "session_id": session_id
        }

    async def explain(self, text: str):
        """
        AI 助读/解释
        """
        template = """请对以下技术文本进行摘要和解释，如果是代码请解释其功能：

文本内容：
{text}

解释："""
        
        prompt = ChatPromptTemplate.from_template(template)
        chain = prompt | self.llm | StrOutputParser()
        
        response = await chain.ainvoke({"text": text})
        return {"explanation": response}
