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
    # Debug: Check counts
    doc_count = await Doc.count()
    activity_count = await Activity.count()
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
    # 获取今日 0 点的时间 (UTC)
    now = datetime.utcnow()
    today_start = datetime(now.year, now.month, now.day)
    
    # 并行执行查询
    # 注意：to_list(None) 确保返回所有结果，避免 Motor 报错
    doc_stats_task = Doc.aggregate(doc_pipeline).to_list(None)
    today_active_task = Activity.find(Activity.created_at >= today_start).distinct("author_id")
    
    results = await asyncio.gather(doc_stats_task, today_active_task)
    
    logger.info(f"Dashboard Overview Results: {results}")

    doc_stats = results[0][0] if results[0] else {
        "total_docs": 0, "total_words": 0, "total_reads": 0, "total_likes": 0
    }
    today_active_users_count = len(results[1])
    
    return {
        **doc_stats,
        "today_active_users": today_active_users_count
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
