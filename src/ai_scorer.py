# src/ai_scorer.py
# Re-export from pipeline.ai_scorer
try:
    from src.pipeline.ai_scorer import evaluate_job_with_ai, JobEvaluation
except ImportError:
    from pipeline.ai_scorer import evaluate_job_with_ai, JobEvaluation

__all__ = ["evaluate_job_with_ai", "JobEvaluation"]
