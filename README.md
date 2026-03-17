# LPU RAG - University Management System Assistant  (by Vicky & Jashanprit)

A production-ready Generative AI chatbot built with **Django**, **LlamaIndex**, and **AWS Bedrock**. This system serves as an intelligent assistant for Lovely Professional University (LPU), providing accurate information about courses, rules, and campus life using Retrieval-Augmented Generation (RAG).

## 🏗 system Architecture

```mermaid
graph TD
    subgraph Client_Layer [Client Layer]
        User((User))
        Browser[Web Browser]
    end

    subgraph App_Layer [Application Layer - AWS App Runner]
        Django[Django Web Server]
        Auth[Auth System]
        ChatUI[Chat Interface]
        subgraph Logic [RAG Logic - LlamaIndex]
            Agent[ReAct Agent]
            Retriever[Amazon KB Retriever]
        end
    end

    subgraph AI_Data_Layer [AI & Data Layer]
        GH_Models[GitHub Models - GPT-4o]
        Bedrock[Amazon Bedrock Knowledge Base]
        Supabase[(Supabase - PostgreSQL)]
    end

    User <--> Browser
    Browser <--> ChatUI
    ChatUI <--> Django
    Django <--> Auth
    Django <--> Agent
    Agent <--> GH_Models
    Agent <--> Retriever
    Retriever <--> Bedrock
    Bedrock <--> Supabase
```

## 🔄 RAG Workflow

This diagram illustrates the decision logic behind every response, including the robust fallback mechanism.

```mermaid
flowchart TD
    A[User Message Received] --> B{Initialize Agent?}
    B -- Success --> C[Query ReAct Agent]
    B -- Failure --> D[Initialize Raw Retriever]
    
    C --> E{LLM Responded?}
    E -- Yes --> F[Display AI Response]
    E -- No --> D
    
    D --> G{Data Found?}
    G -- Yes --> H[Display Raw Snippets <br/> with Warning]
    G -- No --> I[Display Friendly Error]
    
    F --> J[Save to Database]
    H --> J
    I --> J
```

## 📡 Sequence Diagram

```mermaid
sequenceDiagram
    participant U as User
    participant D as Django (View)
    participant A as LlamaIndex Agent
    participant K as Bedrock KB
    participant L as LLM (GPT-4o)

    U->>D: Send Message
    D->>A: Process Request
    A->>K: Retrieve Context
    K-->>A: Context Chunks
    A->>L: Context + Query
    L-->>A: Structured Answer
    A-->>D: response_text
    D-->>U: Display Answer
```

## 🛠 Features
- **Intelligent RAG**: Uses LlamaIndex ReAct agent for multi-step reasoning.
- **Robust Fallback**: Automatically switches to raw vector retrieval if the LLM or API is unavailable.
- **AWS Integrated**: Leverages Amazon Bedrock Knowledge Bases for enterprise-grade retrieval.
- **Data Persistence**: Managed by **Supabase (PostgreSQL)** for secure and scalable history management.
- **Enterprise Grade**: Deployed via Docker on **AWS App Runner**.
- **Secure**: Integrated with Django's authentication and CSRF protection.

## 🚀 Getting Started

### Prerequisites
- Python 3.12+
- Docker (optional)
- AWS Credentials (with Bedrock access)
- GitHub Token (for LLM inference)

### Installation
1. Clone the repo:
   ```bash
   git clone https://github.com/MAVIcVICKY/LPU_RAG.git
   cd LPU_RAG
   ```
2. Setup environment variables:
   Create a `.env` file based on `.env.example`.
3. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```
4. Run migrations:
   ```bash
   python manage.py migrate
   ```
5. Start server:
   ```bash
   python manage.py runserver
   ```
