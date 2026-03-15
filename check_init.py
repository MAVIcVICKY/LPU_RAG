import os
import logging
import traceback
from dotenv import load_dotenv
load_dotenv()

try:
    from llama_index.retrievers.bedrock import AmazonKnowledgeBasesRetriever
    from llama_index.llms.openai import OpenAI
    from llama_index.core.query_engine import RetrieverQueryEngine
    from llama_index.core.tools import QueryEngineTool
    try:
        from llama_index.core.agent import ReActAgent
    except ImportError:
        from llama_index.core.agent.workflow import ReActAgent
    from llama_index.core.llms import ChatMessage, MessageRole
    from llama_index.core import Settings
    print("Imports successful")
except ImportError as e:
    print(f"ImportError: {e}")
    exit(1)

github_token = os.getenv("GITHUB_TOKEN")
github_model = os.getenv("GITHUB_MODEL", "gpt-4o")
aws_region = os.getenv("AWS_REGION") or os.getenv("AWS_DEFAULT_REGION") or "us-east-1"

try:
    retriever = AmazonKnowledgeBasesRetriever(
        knowledge_base_id=os.getenv("BEDROCK_KNOWLEDGE_BASE_ID"),
        retrieval_config={"vectorSearchConfiguration": {"numberOfResults": 3}},
        region_name=aws_region
    )
    print("Retriever initialized")

    if github_token:
        llm = OpenAI(
            model=github_model,
            api_key=github_token,
            api_base="https://models.github.ai/inference",
        )
        Settings.llm = llm
        print(f"LLM initialized with model {github_model}")

        _knowledge_base_tool = QueryEngineTool.from_defaults(
            query_engine=RetrieverQueryEngine(retriever=retriever),
            name="amazon_knowledge_base",
            description="A vector database of knowledge about the university system and related data.",
        )

        # Try various ways to create the agent for compatibility
        try:
            if hasattr(ReActAgent, 'from_tools'):
                agent = ReActAgent.from_tools(
                    tools=[_knowledge_base_tool],
                    llm=llm,
                    system_prompt="You are a helpful AI assistant."
                )
            else:
                agent = ReActAgent(
                    tools=[_knowledge_base_tool],
                    llm=llm,
                    system_prompt="You are a helpful AI assistant."
                )
        except Exception as e:
            print(f"Standard init failed, trying direct ReActAgent: {e}")
            agent = ReActAgent(
                tools=[_knowledge_base_tool],
                llm=llm,
                system_prompt="You are a helpful AI assistant."
            )
        print("Agent initialized successfully")
    else:
        print("GITHUB_TOKEN missing")

except Exception as e:
    print(f"Error: {e}")
    traceback.print_exc()
