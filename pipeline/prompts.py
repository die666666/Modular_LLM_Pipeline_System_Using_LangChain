"""
prompts.py -- PromptLibrary
FIXED: All literal JSON curly braces escaped as {{ }} so LangChain
does not mistake them for template variables.
"""

from langchain_core.prompts import ChatPromptTemplate, PromptTemplate


class PromptLibrary:

    # -- Financial Extraction ---------------------------------------------

    @staticmethod
    def financial_extraction_default() -> ChatPromptTemplate:
        return ChatPromptTemplate.from_messages([
            (
                "system",
                (
                    "You are a senior financial analyst. Extract structured data from "
                    "the provided text. Return ONLY valid JSON matching this schema:\n"
                    "{{\n"
                    '  "company": "string or null",\n'
                    '  "revenue": "string or null",\n'
                    '  "net_income": "string or null",\n'
                    '  "ebitda": "string or null",\n'
                    '  "key_metrics": ["list of strings"],\n'
                    '  "risks": ["list of strings"],\n'
                    '  "outlook": "string or null"\n'
                    "}}\n"
                    "If a field is not found, use null. Output JSON only -- no prose, "
                    "no markdown fences."
                ),
            ),
            ("user", "Financial text:\n\n{text}"),
        ])

    @staticmethod
    def financial_extraction_alt() -> ChatPromptTemplate:
        return ChatPromptTemplate.from_messages([
            (
                "system",
                (
                    "You are a CFA-level analyst reading an earnings report. "
                    "Carefully identify every financial figure mentioned. "
                    "Return a JSON object with exactly these keys: "
                    "company, revenue, net_income, ebitda, key_metrics, risks, outlook. "
                    "key_metrics and risks must be arrays of strings. "
                    "All other fields are strings. Use null when data is missing. "
                    "Return only raw JSON -- no markdown, no explanation."
                ),
            ),
            ("user", "Analyze this:\n\n{text}"),
        ])

    # -- Summarization ----------------------------------------------------

    @staticmethod
    def summarization_default() -> ChatPromptTemplate:
        return ChatPromptTemplate.from_messages([
            (
                "system",
                (
                    "You are a professional document summarizer. "
                    "Produce a concise executive summary in exactly 3 sections:\n"
                    "1. Key Points (3-5 bullet points)\n"
                    "2. Critical Findings (2-3 sentences)\n"
                    "3. Recommended Actions (2-3 bullet points)\n\n"
                    "Be precise, avoid filler, use professional language."
                ),
            ),
            ("user", "Document to summarize:\n\n{document}"),
        ])

    @staticmethod
    def summarization_alt() -> ChatPromptTemplate:
        return ChatPromptTemplate.from_messages([
            (
                "system",
                (
                    "Summarize the following document for a C-suite executive "
                    "who has 2 minutes to read it. Lead with the single most important "
                    "insight. Use plain language and short sentences."
                ),
            ),
            ("user", "{document}"),
        ])

    # -- Multi-step Reasoning ---------------------------------------------

    @staticmethod
    def reasoning_decompose() -> ChatPromptTemplate:
        return ChatPromptTemplate.from_messages([
            (
                "system",
                (
                    "You are an expert problem solver. Break the question into "
                    "clear numbered reasoning steps. Think carefully before concluding."
                ),
            ),
            ("user", "Problem: {problem}"),
        ])

    @staticmethod
    def reasoning_synthesize() -> ChatPromptTemplate:
        return ChatPromptTemplate.from_messages([
            (
                "system",
                (
                    "Given the reasoning steps below, produce a final concise answer. "
                    "State your confidence level (High / Medium / Low) and explain why."
                ),
            ),
            ("user", "Reasoning steps:\n\n{steps}\n\nFinal answer:"),
        ])

    @staticmethod
    def reasoning_critique() -> ChatPromptTemplate:
        return ChatPromptTemplate.from_messages([
            (
                "system",
                (
                    "You are a critical reviewer. Identify logical flaws, "
                    "unsupported assumptions, or missing considerations in the reasoning."
                ),
            ),
            ("user", "Reasoning to critique:\n\n{reasoning}"),
        ])