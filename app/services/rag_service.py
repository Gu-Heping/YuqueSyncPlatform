import os
import re
import asyncio
# 强制禁用本地连接的代理，防止 502 Bad Gateway
os.environ["NO_PROXY"] = "localhost,127.0.0.1"

import logging
from typing import List, Optional
from bs4 import BeautifulSoup
from qdrant_client import QdrantClient
from langchain_qdrant import QdrantVectorStore
from langchain_openai import OpenAIEmbeddings, ChatOpenAI
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_core.documents import Document
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser
from langchain_core.messages import HumanMessage, AIMessage

from app.core.config import settings
from app.models.schemas import Doc, ChatSession, ChatMessage, Member, User

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
        2. Retrieval with Metadata
        3. Answer Generation
        4. Memory Persistence
        """
        # 0. 获取/创建会话
        if not session_id:
            session = ChatSession(title=query[:20])
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

        # Step 2: Retrieval with Metadata (携带元数据的检索)
        # 使用改写后的 query 进行检索
        docs = await self.search(final_query, limit=5, repo_id=repo_id)
        
        def format_docs(docs):
            formatted = []
            for d in docs:
                meta = d
                # 尝试获取更多元数据，这里假设 search 返回的 dict 已经包含了 metadata
                title = meta.get("title", "未知文档")
                author = meta.get("author_name", meta.get("user_id", "未知作者"))
                date = meta.get("updated_date", "未知日期")
                content = meta.get("content", "")
                
                formatted.append(f"<Document>\nTitle: {title}\nAuthor: {author}\nDate: {date}\nContent: {content}\n</Document>")
            return "\n\n".join(formatted)

        context_text = format_docs(docs)

        # Step 3: Answer Generation (生成回答)
        qa_system_prompt = """你是一位专业的团队技术顾问。请基于以下检索到的上下文（Context），回答用户的问题。
请在回答中尽可能引用文档的作者和最后更新时间，以增加可信度。
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
            "input": final_query # 使用改写后的 query 还是原始 query? 通常 RAG 生成阶段使用原始 query 配合 history，或者改写后的。
            # 这里使用 final_query 更稳妥，因为它包含了完整语义。但如果 prompt 里有 chat_history，也可以用原始 query。
            # 鉴于我们已经改写了 query 用于检索，生成阶段为了保持一致性，且 prompt 包含 history，我们可以用原始 query 让 LLM 看到用户的真实输入，
            # 或者用 final_query。标准做法是：检索用 standalone query，生成用 original query + history + context。
            # 但为了简化，且 final_query 已经包含了 history 的语义，我们可以只传 final_query 或者 original query。
            # 让我们传 original query，因为 prompt 里有 chat_history placeholder。
        })
        
        # Step 4: Memory Persistence (记忆存储)
        # 保存用户提问
        await ChatMessage(session_id=session_id, role="user", content=query).insert()
        
        # 构造 Sources
        sources = []
        for d in docs:
            s = d.copy()
            s.pop('content', None)
            s.pop('score', None)
            sources.append(s)

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
