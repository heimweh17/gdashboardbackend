"""
AI insights router with weekly limit enforcement.
"""
import json
from datetime import datetime, timedelta
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.core.config import settings
from app.db.database import get_db
from app.db.models import AIUsage, AnalysisRun, User
from app.routers.auth import get_current_user
from app.schemas.ai import InsightRequest, InsightResponse
from app.services.ai_gemini import generate_insight

router = APIRouter()


def check_weekly_limit(user_id: int, db: Session) -> tuple[bool, datetime | None]:
	"""
	Check if user has exceeded weekly limit (1 insight per 7 days).
	
	Returns:
		(is_allowed, retry_after_datetime)
	"""
	seven_days_ago = datetime.utcnow() - timedelta(days=7)
	
	count = (
		db.query(func.count(AIUsage.id))
		.filter(
			AIUsage.user_id == user_id,
			AIUsage.action == "insight",
			AIUsage.created_at >= seven_days_ago,
		)
		.scalar()
	)
	
	if count >= 1:
		# Find the oldest usage in the window to calculate retry_after
		oldest = (
			db.query(AIUsage.created_at)
			.filter(
				AIUsage.user_id == user_id,
				AIUsage.action == "insight",
				AIUsage.created_at >= seven_days_ago,
			)
			.order_by(AIUsage.created_at.asc())
			.first()
		)
		
		if oldest:
			retry_after = oldest[0] + timedelta(days=7)
			return False, retry_after
		
		return False, None
	
	return True, None


@router.post("/insights", response_model=InsightResponse)
def generate_ai_insight(
	request: InsightRequest,
	db: Session = Depends(get_db),
	current_user: User = Depends(get_current_user),
):
	"""
	Generate AI insight from analysis result.
	
	Enforces weekly limit: max 1 insight per user per rolling 7 days.
	"""
	# Check weekly limit
	is_allowed, retry_after = check_weekly_limit(current_user.id, db)
	
	if not is_allowed:
		error_detail = "Weekly limit reached: 1 insight per user per 7 days."
		headers = None
		if retry_after:
			seconds_until = int((retry_after - datetime.utcnow()).total_seconds())
			error_detail += f" Retry after {retry_after.isoformat()} ({seconds_until} seconds)."
			headers = {"Retry-After": str(max(1, seconds_until))}
		
		raise HTTPException(
			status_code=status.HTTP_429_TOO_MANY_REQUESTS,
			detail=error_detail,
			headers=headers,
		)
	
	# Get analysis result
	analysis_result = None
	
	if request.analysis_result:
		analysis_result = request.analysis_result
	elif request.analysis_run_id:
		# Fetch from database
		run = (
			db.query(AnalysisRun)
			.filter(AnalysisRun.id == request.analysis_run_id, AnalysisRun.user_id == current_user.id)
			.first()
		)
		if not run:
			raise HTTPException(status_code=404, detail="Analysis run not found")
		
		try:
			analysis_result = json.loads(run.result_json) if isinstance(run.result_json, str) else run.result_json
		except json.JSONDecodeError:
			raise HTTPException(status_code=400, detail="Invalid analysis result JSON")
	else:
		raise HTTPException(
			status_code=400, detail="Either analysis_result or analysis_run_id must be provided"
		)
	
	if not analysis_result:
		raise HTTPException(status_code=400, detail="No analysis result available")
	
	# Generate insight
	try:
		insight = generate_insight(analysis_result, request.context)
	except ValueError as e:
		raise HTTPException(status_code=500, detail=f"AI service configuration error: {str(e)}")
	except RuntimeError as e:
		raise HTTPException(status_code=500, detail=f"AI service error: {str(e)}")
	except Exception as e:
		raise HTTPException(status_code=500, detail=f"Failed to generate insight: {str(e)}")
	
	# Record usage
	usage = AIUsage(user_id=current_user.id, action="insight")
	db.add(usage)
	db.commit()
	
	# Return response
	meta = {
		"model": settings.gemini_model,
		"generated_at": datetime.utcnow().isoformat(),
		"limit_window_days": 7,
	}
	# Include method if available from Gemini
	if "method" in insight:
		meta["method"] = insight["method"]
	
	return InsightResponse(
		text=insight.get("text", ""),
		highlights=insight.get("highlights", []),
		meta=meta,
	)

