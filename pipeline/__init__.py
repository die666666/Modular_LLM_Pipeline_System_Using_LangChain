"""
AutoChain Pipeline — Elite LangChain + Ollama Package
Financial Intelligence & Document Analysis Engine
"""

__version__ = "2.0.0"
__author__ = "AutoChain"

from pipeline.core import PipelineEngine
from pipeline.chains import FinancialChain, SummarizationChain, ReasoningChain
from pipeline.prompts import PromptLibrary
from pipeline.evaluators import PipelineEvaluator

__all__ = [
    "PipelineEngine",
    "FinancialChain",
    "SummarizationChain",
    "ReasoningChain",
    "PromptLibrary",
    "PipelineEvaluator",
]