# Modular_LLM_Pipeline_System_Using_LangChain
This project demonstrates how to build modular and composable AI workflows using LangChain with a locally hosted LLM powered by Ollama (LLaMA 3.1).
It showcases prompt engineering, sequential runnable chains, parallel execution, and structured output parsing using real-world examples such as translation and car recommendations.


## Features
- Local LLM inference using Ollama
- PromptTemplate and ChatPromptTemplate usage
- RunnableSequence for multi-step execution
- RunnableParallel for concurrent model execution
- StrOutputParser for structured outputs
- Real-world example: Budget-based car recommendation system
- Translation workflow example


## Tech Stack
- Python
- LangChain
- Ollama
- LLaMA 3.1
- RunnableSequence & RunnableParallel


## Workflow Overview
1. User provides input (budget, company, text, etc.)
2. Prompt templates structure the request
3. LLM processes the prompt via Ollama
4. RunnableSequence handles step-by-step reasoning
5. RunnableParallel executes brand comparisons simultaneously
6. Output parser formats final results


## ⚙️ Installation 

```bash
pip install -U langchain langchain-core langchain-ollama ollama
