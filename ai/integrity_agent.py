"""
LangChain-based AI Examination Integrity Report Agent for ExamGuard.
Generates structured, objective examination integrity audit reports using
environment variable API keys (OpenAI / Gemini) or ethical deterministic synthesis.
"""

from ai.report_agent import AIReportAgent, ETHICAL_DISCLAIMER

__all__ = ["AIReportAgent", "ETHICAL_DISCLAIMER"]
