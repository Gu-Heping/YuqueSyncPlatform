from fastapi import APIRouter, Depends, Query
from typing import List, Dict, Any
from datetime import datetime, timedelta
from app.models.schemas import Doc, Activity, Member
from app.api.auth import get_current_user
from beanie.operators import In, GTE, LTE

router = APIRouter()

@router.get("/overview")
async def get_overview(
    start_date: datetime = Query(default=None),
    end_date: datetime = Query(default=None),
    current_user: Member = Depends(get_current_user)
):
    """
    获取全局概览数据
    """
    if not end_date:
        end_date = datetime.utcnow()
    if not start_date:
        start_date = end_date - timedelta(days=30)

    # 1. 累计数据 (Total)
    # 注意：累计数据通常是全量的，不受日期过滤影响，或者根据需求定义。
    # 这里我们定义：总文档数等是全量的。
    total_docs = await Doc.find(Doc.type == "DOC").count()
    
    # 聚合计算总字数、总阅读、总点赞
    pipeline_total = [
        {"$match": {"type": "DOC"}},
        {"$group": {
            "_id": None,
            "total_words": {"$sum": "$word_count"},
            "total_reads": {"$sum": "$read_count"},
            "total_likes": {"$sum": "$likes_count"}
        }}
    ]
    total_stats = await Doc.aggregate(pipeline_total).to_list()
    total_words = total_stats[0]["total_words"] if total_stats else 0
    total_reads = total_stats[0]["total_reads"] if total_stats else 0
    total_likes = total_stats[0]["total_likes"] if total_stats else 0

    # 2. 今日数据 (Today)
    today_start = datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)
    
    # 今日新增文档 (兼容 created_at 为空的情况，尝试使用 first_published_at)
    # Beanie 不支持复杂的 $ifNull 查询，这里我们分两步或直接使用聚合
    pipeline_today_docs = [
        {
            "$match": {
                "type": "DOC",
                "$expr": {
                    "$gte": [
                        {"$ifNull": ["$created_at", "$first_published_at", "$updated_at"]},
                        today_start
                    ]
                }
            }
        },
        {"$count": "count"}
    ]
    today_docs_result = await Doc.aggregate(pipeline_today_docs).to_list()
    new_docs_today = today_docs_result[0]["count"] if today_docs_result else 0
    
    # 今日活跃人数 (基于 Activity)
    active_users_today = len(await Activity.find(
        Activity.created_at >= today_start
    ).distinct("author_id"))

    return {
        "total_docs": total_docs,
        "total_words": total_words,
        "total_reads": total_reads,
        "total_likes": total_likes,
        "new_docs_today": new_docs_today,
        "active_users_today": active_users_today
    }

@router.get("/trends")
async def get_trends(
    start_date: datetime = Query(default=None),
    end_date: datetime = Query(default=None),
    current_user: Member = Depends(get_current_user)
):
    """
    获取趋势分析数据 (按天分组)
    """
    if not end_date:
        end_date = datetime.utcnow()
    if not start_date:
        start_date = end_date - timedelta(days=30)

    # 1. 每日新增文档趋势
    pipeline_docs = [
        {
            "$match": {
                "type": "DOC",
                "$expr": {
                    "$and": [
                        {"$gte": [{"$ifNull": ["$created_at", "$first_published_at", "$updated_at"]}, start_date]},
                        {"$lte": [{"$ifNull": ["$created_at", "$first_published_at", "$updated_at"]}, end_date]}
                    ]
                }
            }
        },
        {
            "$group": {
                "_id": {
                    "$dateToString": {
                        "format": "%Y-%m-%d", 
                        "date": {"$ifNull": ["$created_at", "$first_published_at", "$updated_at"]}
                    }
                },
                "count": {"$sum": 1}
            }
        },
        {"$sort": {"_id": 1}}
    ]
    docs_trend = await Doc.aggregate(pipeline_docs).to_list()
    docs_map = {item["_id"]: item["count"] for item in docs_trend}

    # 2. 每日活跃人数趋势
    pipeline_activity = [
        {
            "$match": {
                "created_at": {"$gte": start_date, "$lte": end_date}
            }
        },
        {
            "$group": {
                "_id": {
                    "date": {"$dateToString": {"format": "%Y-%m-%d", "date": "$created_at"}},
                    "user": "$author_id"
                }
            }
        },
        {
            "$group": {
                "_id": "$_id.date",
                "count": {"$sum": 1}
            }
        },
        {"$sort": {"_id": 1}}
    ]
    activity_trend = await Activity.aggregate(pipeline_activity).to_list()
    activity_map = {item["_id"]: item["count"] for item in activity_trend}

    # 3. 合并并填充日期 (补0)
    result = []
    current = start_date
    while current <= end_date:
        date_str = current.strftime("%Y-%m-%d")
        result.append({
            "date": date_str,
            "new_docs": docs_map.get(date_str, 0),
            "active_users": activity_map.get(date_str, 0)
        })
        current += timedelta(days=1)

    return result

@router.get("/rankings")
async def get_rankings(
    current_user: Member = Depends(get_current_user)
):
    """
    获取英雄榜数据 (Top 10)
    """
    # 1. 笔耕不辍榜 (Word Count)
    pipeline_words = [
        {"$match": {"type": "DOC", "user_id": {"$ne": None}}},
        {"$group": {
            "_id": "$user_id",
            "total_count": {"$sum": "$word_count"}
        }},
        {"$sort": {"total_count": -1}},
        {"$limit": 10}
    ]
    word_rankings = await Doc.aggregate(pipeline_words).to_list()

    # 2. 人气之星榜 (Likes Count)
    pipeline_likes = [
        {"$match": {"type": "DOC", "user_id": {"$ne": None}}},
        {"$group": {
            "_id": "$user_id",
            "total_count": {"$sum": "$likes_count"}
        }},
        {"$sort": {"total_count": -1}},
        {"$limit": 10}
    ]
    like_rankings = await Doc.aggregate(pipeline_likes).to_list()

    # 3. 知识传播榜 (Read Count)
    pipeline_reads = [
        {"$match": {"type": "DOC", "user_id": {"$ne": None}}},
        {"$group": {
            "_id": "$user_id",
            "total_count": {"$sum": "$read_count"}
        }},
        {"$sort": {"total_count": -1}},
        {"$limit": 10}
    ]
    read_rankings = await Doc.aggregate(pipeline_reads).to_list()

    # 4. 补充用户信息
    # 收集所有涉及的 user_id
    user_ids = set()
    for r in word_rankings + like_rankings + read_rankings:
        if r["_id"]:
            user_ids.add(r["_id"])
    
    members = await Member.find(In(Member.yuque_id, list(user_ids))).to_list()
    member_map = {m.yuque_id: m for m in members}

    def format_ranking(rankings):
        formatted = []
        for item in rankings:
            uid = item["_id"]
            member = member_map.get(uid)
            formatted.append({
                "user_id": uid,
                "name": member.name if member else "Unknown",
                "avatar_url": member.avatar_url if member else None,
                "value": item["total_count"]
            })
        return formatted

    return {
        "word_rankings": format_ranking(word_rankings),
        "like_rankings": format_ranking(like_rankings),
        "read_rankings": format_ranking(read_rankings)
    }
