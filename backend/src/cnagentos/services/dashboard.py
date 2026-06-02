"""Dashboard statistics aggregation service (Phase 8)."""

import re
from collections import Counter
from datetime import date, datetime, timedelta, timezone
from uuid import uuid4

from sqlalchemy import func, select, text
from sqlalchemy.ext.asyncio import AsyncSession

from cnagentos.models.entities import (
    CollectionTask,
    KnowledgeItem,
    ModelCallLog,
    QaSession,
    SentimentTask,
    User,
    WatchSource,
)


def _naive_utc() -> datetime:
    return datetime.now(timezone.utc).replace(tzinfo=None)


class DashboardService:
    """Aggregate cross-module statistics for the smart dashboard."""

    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def get_stats(self) -> dict:
        """Return aggregated statistics across all major modules."""
        import asyncio

        results = await asyncio.gather(
            self._count_knowledge_items(),
            self._count_watch_sources(),
            self._count_collection_tasks(),
            self._count_qa_sessions(),
            self._count_users(),
            self._count_chat_messages(),
            self._count_model_calls(),
            self._collection_health(),
            self._latest_sentiment_summary(),
            self._source_distribution(),
            return_exceptions=True,
        )

        def _safe(val, default):
            return val if not isinstance(val, Exception) else default

        return {
            "knowledge_items": _safe(results[0], {"total": 0}),
            "watch_sources": _safe(results[1], {"total": 0}),
            "collection_tasks": _safe(results[2], {"total": 0}),
            "qa_sessions": _safe(results[3], {"total": 0}),
            "users": _safe(results[4], {"total": 0, "active_today": 0}),
            "chat_messages": _safe(results[5], {"total_24h": 0, "total": 0}),
            "model_calls": _safe(results[6], {"total": 0, "total_today": 0, "by_purpose": {}, "avg_latency_ms": 0, "avg_total_tokens": 0}),
            "collection_health": _safe(results[7], {"total_success": 0, "total_failure": 0, "success_rate": 0, "recent_failures_7d": 0}),
            "sentiment_summary": _safe(results[8], None),
            "source_distribution": _safe(results[9], []),
            "updated_at": _naive_utc().isoformat(),
        }

    async def _count_knowledge_items(self) -> dict:
        rows = (
            await self.session.execute(
                select(KnowledgeItem.status, func.count(KnowledgeItem.id))
                .group_by(KnowledgeItem.status)
            )
        ).all()
        total = 0
        result = {}
        for status, cnt in rows:
            result[status] = cnt
            total += cnt
        result["total"] = total
        return result

    async def _count_watch_sources(self) -> dict:
        rows = (
            await self.session.execute(
                select(WatchSource.status, func.count(WatchSource.id))
                .group_by(WatchSource.status)
            )
        ).all()
        total = 0
        result = {}
        for status, cnt in rows:
            result[status] = cnt
            total += cnt
        result["total"] = total
        return result

    async def _count_collection_tasks(self) -> dict:
        rows = (
            await self.session.execute(
                select(CollectionTask.status, func.count(CollectionTask.id))
                .group_by(CollectionTask.status)
            )
        ).all()
        total = 0
        result = {}
        for status, cnt in rows:
            result[status] = cnt
            total += cnt
        result["total"] = total
        return result

    async def _count_qa_sessions(self) -> dict:
        rows = (
            await self.session.execute(
                select(QaSession.status, func.count(QaSession.id))
                .group_by(QaSession.status)
            )
        ).all()
        total = 0
        result = {}
        for status, cnt in rows:
            result[status] = cnt
            total += cnt
        result["total"] = total
        return result

    async def _count_users(self) -> dict:
        total = (await self.session.scalar(select(func.count(User.id)))) or 0
        today = _naive_utc().date()
        today_start = datetime(today.year, today.month, today.day, tzinfo=None)
        # Count users who logged in today via auth_sessions (approximate active count)
        active_today = (
            await self.session.scalar(
                select(func.count(func.distinct(ModelCallLog.caller_user_id)))
                .where(ModelCallLog.started_at >= today_start)
            )
        ) or 0
        return {"total": total, "active_today": active_today}

    async def _count_chat_messages(self) -> dict:
        """Count total messages and last 24h messages (aggregate only, no content)."""
        from cnagentos.models.entities import Message

        total = (await self.session.scalar(select(func.count(Message.id)))) or 0
        since = _naive_utc().replace(hour=0, minute=0, second=0, microsecond=0)
        last_24h = (
            await self.session.scalar(
                select(func.count(Message.id))
                .where(Message.created_at >= since)
            )
        ) or 0
        return {"total_24h": last_24h, "total": total}

    async def _count_model_calls(self) -> dict:
        """Aggregate model call statistics by purpose."""
        # Total calls by purpose
        rows = (
            await self.session.execute(
                select(
                    ModelCallLog.purpose,
                    func.count(ModelCallLog.id),
                    func.avg(ModelCallLog.latency_ms),
                    func.avg(ModelCallLog.total_tokens),
                )
                .where(ModelCallLog.purpose.isnot(None))
                .group_by(ModelCallLog.purpose)
            )
        ).all()

        today = _naive_utc().date()
        today_start = datetime(today.year, today.month, today.day, tzinfo=None)
        total_today = (
            await self.session.scalar(
                select(func.count(ModelCallLog.id))
                .where(ModelCallLog.started_at >= today_start)
            )
        ) or 0

        # Count failed calls by purpose
        failed_rows = (
            await self.session.execute(
                select(
                    ModelCallLog.purpose,
                    func.count(ModelCallLog.id),
                )
                .where(ModelCallLog.purpose.isnot(None))
                .where(ModelCallLog.status == "failed")
                .group_by(ModelCallLog.purpose)
            )
        ).all()
        failed_map = {r[0]: r[1] for r in failed_rows}

        by_purpose = {}
        total_calls = 0
        weighted_latency = 0.0
        weighted_tokens = 0.0

        for purpose, cnt, avg_lat, avg_tok in rows:
            cnt = cnt or 0
            by_purpose[purpose] = {
                "count": cnt,
                "failed": failed_map.get(purpose, 0) or 0,
            }
            total_calls += cnt
            if avg_lat:
                weighted_latency += float(avg_lat) * cnt
            if avg_tok:
                weighted_tokens += float(avg_tok) * cnt

        avg_latency_ms = round(weighted_latency / total_calls, 1) if total_calls else 0.0
        avg_total_tokens = round(weighted_tokens / total_calls, 1) if total_calls else 0.0

        return {
            "total": total_calls,
            "total_today": total_today,
            "by_purpose": by_purpose,
            "avg_latency_ms": avg_latency_ms,
            "avg_total_tokens": avg_total_tokens,
        }

    async def _collection_health(self) -> dict:
        """Calculate collection task success rate and health metrics."""
        row = (
            await self.session.execute(
                select(
                    func.sum(CollectionTask.item_success_count),
                    func.sum(CollectionTask.item_failure_count),
                )
            )
        ).first()

        total_success = row[0] or 0
        total_failure = row[1] or 0
        total = total_success + total_failure
        success_rate = round(total_success / total * 100, 1) if total else 0.0

        # Recent failures (last 7 days)
        since = _naive_utc().replace(hour=0, minute=0, second=0, microsecond=0)
        seven_days_ago = since - timedelta(days=7)
        recent_failures = (
            await self.session.scalar(
                select(func.count(CollectionTask.id))
                .where(CollectionTask.created_at >= seven_days_ago)
                .where(CollectionTask.status.in_(["failed", "partial_failed"]))
            )
        ) or 0

        return {
            "total_success": total_success,
            "total_failure": total_failure,
            "success_rate": success_rate,
            "recent_failures_7d": recent_failures,
        }

    async def _latest_sentiment_summary(self) -> dict | None:
        """Return the latest completed sentiment task with risk summary."""
        task = (
            await self.session.execute(
                select(SentimentTask)
                .where(SentimentTask.status == "completed")
                .order_by(SentimentTask.completed_at.desc())
                .limit(1)
            )
        ).scalar_one_or_none()

        if not task:
            return None

        # Load the first report
        from cnagentos.models.entities import SentimentReport

        report = (
            await self.session.execute(
                select(SentimentReport)
                .where(SentimentReport.task_id == task.id)
                .order_by(SentimentReport.created_at.desc())
                .limit(1)
            )
        ).scalar_one_or_none()

        summary_text = report.summary_text or "" if report else ""

        # Extract risk level from summary text (heuristic)
        risk_level = None
        if "风险等级" in summary_text:
            m = re.search(r"风险等级[：:]\s*([低中高])", summary_text)
            if m:
                risk_level = m.group(1)

        return {
            "latest_task_name": task.name,
            "latest_status": task.status,
            "risk_level": risk_level,
            "summary_snippet": summary_text[:300] if summary_text else "",
            "completed_at": task.completed_at.isoformat() if task.completed_at else "",
        }

    async def _source_distribution(self) -> list[dict]:
        """Get knowledge item distribution by data source (Top 15 + others)."""
        rows = (
            await self.session.execute(
                select(
                    KnowledgeItem.source_id,
                    func.count(KnowledgeItem.id).label("item_count"),
                )
                .where(KnowledgeItem.source_id.isnot(None))
                .group_by(KnowledgeItem.source_id)
                .order_by(func.count(KnowledgeItem.id).desc())
                .limit(15)
            )
        ).all()

        if not rows:
            return []

        source_ids = [r[0] for r in rows]
        sources = {}
        if source_ids:
            source_rows = (
                await self.session.execute(
                    select(WatchSource.id, WatchSource.name, WatchSource.source_type, WatchSource.status)
                    .where(WatchSource.id.in_(source_ids))
                )
            ).all()
            sources = {r[0]: {"name": r[1], "source_type": r[2], "status": r[3]} for r in source_rows}

        result = []
        for source_id, item_count in rows:
            info = sources.get(
                source_id,
                {"name": str(source_id)[:8], "source_type": "unknown", "status": "unknown"},
            )
            result.append({
                "source_name": info["name"],
                "source_type": info["source_type"],
                "item_count": item_count,
                "status": info["status"],
            })

        return result

    async def get_trends(self, days: int = 30) -> dict:
        """Return daily trend data for knowledge items, QA questions, and messages."""
        from cnagentos.models.entities import Message, QaMessage

        days = min(max(days, 1), 90)
        since = _naive_utc().replace(hour=0, minute=0, second=0, microsecond=0)
        # Build date list for filling gaps
        date_list = [
            (
                date.fromordinal(
                    since.toordinal() - i
                ).isoformat()
            )
            for i in range(days - 1, -1, -1)
        ]

        def _fill(tuples: list[tuple], key: str) -> list[dict]:
            """Fill gaps in daily series with zero counts."""
            counts = {str(d): c for d, c in tuples if d}
            return [{"date": d, key: counts.get(d, 0)} for d in date_list]

        knowledge_tuples = (
            (
                await self.session.execute(
                    select(
                        func.date(KnowledgeItem.collected_at).label("d"),
                        func.count(KnowledgeItem.id),
                    )
                    .where(KnowledgeItem.collected_at >= since)
                    .group_by(text("d"))
                )
            )
            .all()
        )

        qa_tuples = (
            (
                await self.session.execute(
                    select(
                        func.date(QaMessage.created_at).label("d"),
                        func.count(QaMessage.id),
                    )
                    .where(QaMessage.created_at >= since)
                    .where(QaMessage.role == "user")
                    .group_by(text("d"))
                )
            )
            .all()
        )

        msg_tuples = (
            (
                await self.session.execute(
                    select(
                        func.date(Message.created_at).label("d"),
                        func.count(Message.id),
                    )
                    .where(Message.created_at >= since)
                    .group_by(text("d"))
                )
            )
            .all()
        )

        model_call_tuples = (
            await self.session.execute(
                select(
                    func.date(ModelCallLog.started_at).label("d"),
                    func.count(ModelCallLog.id),
                )
                .where(ModelCallLog.started_at >= since)
                .group_by(text("d"))
            )
        ).all()

        model_token_tuples = (
            await self.session.execute(
                select(
                    func.date(ModelCallLog.started_at).label("d"),
                    func.sum(ModelCallLog.total_tokens),
                )
                .where(ModelCallLog.started_at >= since)
                .where(ModelCallLog.total_tokens.isnot(None))
                .group_by(text("d"))
            )
        ).all()

        return {
            "knowledge_items": _fill(knowledge_tuples, "count"),
            "qa_questions": _fill(qa_tuples, "count"),
            "chat_messages": _fill(msg_tuples, "count"),
            "model_calls": _fill(model_call_tuples, "count"),
            "model_tokens": _fill(model_token_tuples, "count"),
        }

    async def get_keywords(self, limit: int = 50) -> list[dict]:
        """Extract keywords from available knowledge item titles and summaries."""
        limit = min(max(limit, 10), 200)
        items = (
            (
                await self.session.execute(
                    select(KnowledgeItem.title, KnowledgeItem.summary)
                    .where(KnowledgeItem.status == "available")
                    .limit(500)
                )
            )
            .all()
        )

        stop_words = {
            "的", "了", "在", "是", "我", "有", "和", "就", "不", "人", "都", "一",
            "一个", "上", "也", "很", "到", "说", "要", "去", "你", "会", "着",
            "没有", "看", "好", "自己", "这", "他", "她", "它", "们", "那", "些",
            "与", "及", "或", "但", "而", "从", "被", "把", "对", "等", "可以",
            "进行", "使用", "通过", "以及", "并且", "因为", "所以", "如果",
            "the", "a", "an", "is", "are", "was", "were", "be", "been",
            "have", "has", "had", "do", "does", "did", "will", "would",
            "can", "could", "may", "might", "shall", "should", "this",
            "that", "these", "those", "it", "its", "they", "them",
            "for", "with", "about", "into", "over", "after", "before",
            "and", "but", "or", "not", "so", "if", "then", "than",
            "also", "very", "just", "each", "all", "any", "both",
        }

        counter: Counter = Counter()
        word_pattern = re.compile(r"[a-zA-Z一-鿿]{2,}")

        for title, summary in items:
            text_content = (title or "") + " " + (summary or "")
            words = word_pattern.findall(text_content.lower())
            for w in words:
                if w not in stop_words:
                    counter[w] += 1

        most_common = counter.most_common(limit)
        return [{"word": word, "count": count} for word, count in most_common]
