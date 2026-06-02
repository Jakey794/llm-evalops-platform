## Planned Architecture

```txt
frontend/ Next.js + TypeScript + Tailwind
        |
        v
backend/ FastAPI + Python + Pydantic
        |
        v
PostgreSQL
        |
        v
LLM providers + grader engine + CI eval gate
```