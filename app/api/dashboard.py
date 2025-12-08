from fastapi import APIRouter, Depends
from typing import List, Dict, Any
from datetime import datetime, timedelta
from app.models.schemas import Doc, Activity, Member
from app.api.auth import get_current_user
from beanie.operators import In
import asyncio
import logging

logger = logging.getLogger(__name__)

router = APIRouter()

@router.get("/overview")
async def get_dashboard_overview(current_user: Member = Depends(get_current_user)):
    """
    获取全局概览数据
    """
    # 使用 motor collection 直接操作，绕过 Beanie 可能存在的聚合转换问题
    db_docs = Doc.get_motor_collection()
    db_activities = Activity.get_motor_collection()

    # Debug: Check counts
    doc_count = await db_docs.count_documents({})
    activity_count = await db_activities.count_documents({})
    logger.info(f"Dashboard Overview Debug: Doc count: {doc_count}, Activity count: {activity_count}")

    # 1. 文档统计 (Doc)
    doc_pipeline = [
        {
            "$group": {
                "_id": None,
                "total_docs": {"$sum": 1},
                "total_words": {"$sum": "$word_count"},
                "total_reads": {"$sum": "$read_count"},
                "total_likes": {"$sum": "$likes_count"}
            }
        }
    ]
    
    # 2. 今日活跃用户 (Activity)
    now = datetime.utcnow()
    today_start = datetime(now.year, now.month, now.day)
    
    # 并行执行查询
    doc_stats_cursor = db_docs.aggregate(doc_pipeline)
    doc_stats_list = await doc_stats_cursor.to_list(length=1)
    
    today_active_users = await db_activities.distinct("author_id", {"created_at": {"$gte": today_start}})
    
    logger.info(f"Dashboard Overview Results: DocStats={doc_stats_list}, ActiveUsers={len(today_active_users)}")

    doc_stats = doc_stats_list[0] if doc_stats_list else {
        "total_docs": 0, "total_words": 0, "total_reads": 0, "total_likes": 0
    }
    
    # 如果聚合结果为空但 count > 0，说明聚合管道有问题，尝试手动计算（兜底方案）
    if doc_stats["total_docs"] == 0 and doc_count > 0:
        logger.warning("Aggregation returned 0 but docs exist. Falling back to manual sum.")
        # 仅用于调试或临时修复，生产环境应修复聚合
        # 注意：这里只计算前 1000 条以避免性能问题
        sample_docs = await db_docs.find({}, {"word_count": 1, "read_count": 1, "likes_count": 1}).to_list(length=10000)
        doc_stats = {
            "total_docs": doc_count,
            "total_words": sum(d.get("word_count", 0) for d in sample_docs),
            "total_reads": sum(d.get("read_count", 0) for d in sample_docs),
            "total_likes": sum(d.get("likes_count", 0) for d in sample_docs)
        }

    return {
        **doc_stats,
        "today_active_users": len(today_active_users)
    }

@router.get("/trends")
async def get_dashboard_trends(days: int = 30, current_user: Member = Depends(get_current_user)):
    """
    获取最近 30 天的趋势数据 (新增文档 & 活跃人数)
    """
    end_date = datetime.utcnow()
    start_date = end_date - timedelta(days=days)
    
    # 1. 每日新增文档 (Doc created_at)
    doc_trend_pipeline = [
        {
            "$match": {
                "created_at": {"$gte": start_date}
            }
        },
        {
            "$group": {
                "_id": {
                    "$dateToString": {"format": "%Y-%m-%d", "date": "$created_at"}
                },
                "count": {"$sum": 1}
            }
        }
    ]
    
    # 2. 每日活跃人数 (Activity created_at -> author_id distinct)
    # MongoDB 聚合去重计数比较麻烦，通常用 $addToSet 然后 $size
    activity_trend_pipeline = [
        {
            "$match": {
                "created_at": {"$gte": start_date}
            }
        },
        {
            "$group": {
                "_id": {
                    "$dateToString": {"format": "%Y-%m-%d", "date": "$created_at"}
                },
                "authors": {"$addToSet": "$author_id"}
            }
        },
        {
            "$project": {
                "_id": 1,
                "count": {"$size": "$authors"}
            }
        }
    ]
    
    doc_trends_task = Doc.aggregate(doc_trend_pipeline).to_list(None)
    activity_trends_task = Activity.aggregate(activity_trend_pipeline).to_list(None)
    
    results = await asyncio.gather(doc_trends_task, activity_trends_task)
    
    # 格式化数据，补全日期
    doc_data_map = {item["_id"]: item["count"] for item in results[0]}
    activity_data_map = {item["_id"]: item["count"] for item in results[1]}
    
    final_data = []
    for i in range(days):
        date = (start_date + timedelta(days=i)).strftime("%Y-%m-%d")
        final_data.append({
            "date": date,
            "new_docs": doc_data_map.get(date, 0),
            "active_users": activity_data_map.get(date, 0)
        })
        
    return final_data

@router.get("/rankings")
async def get_dashboard_rankings(current_user: Member = Depends(get_current_user)):
    """
    获取排行榜数据 (Top 10)
    """
    limit = 10
    
    # 1. 笔耕不辍榜 (Word Count)
    word_pipeline = [
        {"$group": {"_id": "$user_id", "value": {"$sum": "$word_count"}}},
        {"$sort": {"value": -1}},
        {"$limit": limit}
    ]
    
    # 2. 人气之星榜 (Likes)
    likes_pipeline = [
        {"$group": {"_id": "$user_id", "value": {"$sum": "$likes_count"}}},
        {"$sort": {"value": -1}},
        {"$limit": limit}
    ]
    
    # 3. 知识传播榜 (Reads)
    reads_pipeline = [
        {"$group": {"_id": "$user_id", "value": {"$sum": "$read_count"}}},
        {"$sort": {"value": -1}},
        {"$limit": limit}
    ]
    
    # 并行执行聚合
    tasks = [
        Doc.aggregate(word_pipeline).to_list(None),
        Doc.aggregate(likes_pipeline).to_list(None),
        Doc.aggregate(reads_pipeline).to_list(None)
    ]
    results = await asyncio.gather(*tasks)
    
    # 收集所有涉及的用户 ID
    user_ids = set()
    for rank_list in results:
        for item in rank_list:
            if item["_id"]:
                user_ids.add(item["_id"])
                
    # 批量获取用户信息
    members = await Member.find(In(Member.yuque_id, list(user_ids))).to_list()
    member_map = {m.yuque_id: {"name": m.name, "avatar_url": m.avatar_url} for m in members}
    
    # 组装结果
    def format_rank(data_list):
        formatted = []
        for item in data_list:
            uid = item["_id"]
            if not uid: continue
            user_info = member_map.get(uid, {"name": "Unknown", "avatar_url": ""})
            formatted.append({
                "user_id": uid,
                "name": user_info["name"],
                "avatar_url": user_info["avatar_url"],
                "value": item["value"]
            })
        return formatted

    return {
        "word_rank": format_rank(results[0]),
        "likes_rank": format_rank(results[1]),
        "read_rank": format_rank(results[2])
    }
