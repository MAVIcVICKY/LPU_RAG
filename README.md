# UMS RAG Chatbot — Retrieval-Augmented University Assistant

Built an AI-powered university assistant serving [X] students/staff with sub-second response times, reducing manual support workload by [X]% through intelligent document retrieval from institutional knowledge bases.

## Impact & Key Achievements

*   **Architected** an agentic RAG pipeline using **LlamaIndex ReAct agents** for multi-step reasoning, integrated with **Amazon Bedrock Knowledge Bases** for fully managed document retrieval and embedding generation.
*   **Orchestrated** multi-model AI responses by integrating **Claude (via Amazon Bedrock)** and **GPT-4o (via GitHub Models)**, providing flexible, state-of-the-art inference for university-specific queries.
*   **Deployed** a containerized **Django** application on **AWS App Runner** with auto-scaling, leveraging **Supabase (PostgreSQL)** for structured data and **S3-backed** institutional knowledge.
*   **Implemented** secure infrastructure using **IAM roles**, **AWS SSM Parameter Store**, and SSL encryption, ensuring enterprise-grade multi-tenant compliance and sub-second query latency.

## Tech Stack

- **Framework**: Django (Python)
- **RAG Engine**: LlamaIndex (ReAct Agent)
- **Database**: Supabase (PostgreSQL)
- **AWS Infrastructure**: App Runner (Compute), SSM (Config), IAM (Access Control)
- **Vector Store**: Amazon Bedrock Knowledge Bases (S3 Data Source)
- **LLMs**: Claude (AWS Bedrock), GPT-4o (GitHub Models)
- **DevOps**: Docker, Gunicorn, whitenoise