# Simple LLM Workflow

A simple LLM workflow project using LangChain, LangGraph, and LangSmith.

## Setup

1. Install uv (if not already installed):
```bash
curl -sSf https://install.ultraviolet.rs | sh
```

2. Create and activate a virtual environment:
```bash
uv venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate
```

3. Install dependencies:
```bash
uv pip install -e .
```

4. Set up environment variables:
```bash
cp .env.example .env
```
Then edit the `.env` file with your API keys.

## Usage

Run the example workflow:
```bash
python src/main.py
``` 


## LangSmith
```
langgraph dev
```