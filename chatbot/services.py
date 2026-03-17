import os
import logging
import traceback
import asyncio
import inspect
from dotenv import load_dotenv
import boto3

# Load environment variables
load_dotenv()

logger = logging.getLogger(__name__)

# Global variables to hold initialized components
retriever = None
orchestrator = None # Changed from agent
HAS_LLAMA = False

try:
    try:
        from llama_index.retrievers.bedrock import AmazonKnowledgeBasesRetriever
        from llama_index.llms.openai import OpenAI
        from llama_index.llms.bedrock import Bedrock
        from llama_index.core.query_engine import RetrieverQueryEngine
        from llama_index.core.tools import QueryEngineTool
        from llama_index.core import Settings
        
        try:
            from llama_index.core.llms import ChatMessage, MessageRole
        except Exception:
            # Fallback for older versions or version conflicts during local testing
            try:
                from llama_index.core.base.llms.types import ChatMessage, MessageRole
            except Exception:
                ChatMessage, MessageRole = None, None
        
        try:
            from llama_index.core.agent import ReActAgent
        except Exception:
            try:
                from llama_index.core.agent.react.base import ReActAgent
            except Exception:
                ReActAgent = None
                
        HAS_LLAMA = True
    except Exception as e:
        HAS_LLAMA = False
        logger.error(f"LlamaIndex initialization error (likely local version mismatch): {e}")
except Exception as global_e:
    HAS_LLAMA = False
    logger.error(f"Global AI import failure: {global_e}")

def get_config(env_key, ssm_path=None):
    """Retrieves configuration from environment or AWS SSM Parameter Store."""
    val = os.getenv(env_key)
    if val:
        return val
    if ssm_path:
        try:
            region = os.getenv("AWS_REGION") or os.getenv("AWS_DEFAULT_REGION") or "ap-south-1"
            ssm = boto3.client('ssm', region_name=region)
            response = ssm.get_parameter(Name=ssm_path, WithDecryption=True)
            return response['Parameter']['Value']
        except Exception as e:
            logger.debug(f"SSM Fetch failed for {ssm_path}: {e}")
    return None

def initialize_retriever():
    """Initializes only the retriever (more stable than the agent)."""
    global retriever
    if retriever is not None:
        return retriever
    try:
        aws_region = os.getenv("AWS_REGION") or os.getenv("AWS_DEFAULT_REGION") or "ap-south-1"
        kb_id = get_config("BEDROCK_KNOWLEDGE_BASE_ID", "/rag-app/knowledge-base-id")
        
        if kb_id:
            logger.info(f"Initializing AmazonKnowledgeBasesRetriever with ID: {kb_id}")
            retriever = AmazonKnowledgeBasesRetriever(
                knowledge_base_id=kb_id,
                retrieval_config={"vectorSearchConfiguration": {"numberOfResults": 3}},
                region_name=aws_region
            )
        else:
            logger.warning("No BEDROCK_KNOWLEDGE_BASE_ID found in env or SSM.")
        return retriever
    except Exception as e:
        logger.error(f"Failed to initialize retriever: {e}")
        return None

def initialize_agent():
    """Initializes the Multi-Agent Orchestrator."""
    global orchestrator, retriever
    if orchestrator is not None:
        return orchestrator
    
    if not HAS_LLAMA:
        logger.error("Cannot initialize orchestrator: LlamaIndex missing.")
        return None

    try:
        from .agents import Orchestrator # Local import to avoid circular dependencies
        
        # Configuration retrieval
        github_token = get_config("GITHUB_TOKEN", "/rag-app/github-token")
        github_model = get_config("GITHUB_MODEL", "/rag-app/github-model") or "gpt-4o"
        bedrock_model = get_config("BEDROCK_MODEL_ID", "/rag-app/model-id")
        aws_region = os.getenv("AWS_REGION") or os.getenv("AWS_DEFAULT_REGION") or "ap-south-1"
        
        # Ensure retriever is ready
        curr_retriever = initialize_retriever()
        if not curr_retriever:
            logger.warning("Retriever not initialized; raw data fallback will be used.")
            # We can still proceed if the planner decides DIRECT
            # But let's stay consistent with the original logic for now

        # Initialize LLM
        llm = None
        if github_token:
            logger.info(f"Using GitHub Models (OpenAI wrapper) with model: {github_model}")
            llm = OpenAI(
                model=github_model,
                api_key=github_token,
                api_base="https://models.github.ai/inference"
            )
        elif bedrock_model:
            logger.info(f"Using AWS Bedrock with model: {bedrock_model}")
            llm = Bedrock(
                model=bedrock_model,
                region_name=aws_region
            )
        else:
            logger.error("No LLM configuration found (missing GITHUB_TOKEN and BEDROCK_MODEL_ID).")
            return None

        Settings.llm = llm
        
        # Initialize Orchestrator instead of ReActAgent
        orchestrator = Orchestrator(llm=llm, retriever=curr_retriever)
        return orchestrator
    except Exception as e:
        logger.error(f"Orchestrator initialization error: {e}")
        return None

async def get_agent_response(message, chat_history):
    # Try fully initialized Orchestrator first
    curr_orchestrator = initialize_agent()
    if curr_orchestrator:
        try:
            chat_history_objs = []
            if ChatMessage and MessageRole:
                for msg in chat_history:
                    role = MessageRole.USER if msg["role"] == "user" else MessageRole.ASSISTANT
                    chat_history_objs.append(ChatMessage(role=role, content=msg["content"]))
            
            # Call our new Orchestrator
            response = await curr_orchestrator.handle_query(message, chat_history_objs)
            return response
            
        except Exception as e:
            logger.error(f"Orchestrator execution failed: {e}")
            logger.debug(traceback.format_exc())
    
    # AGGRESSIVE FALLBACK: Raw chunks if LLM/Agent fails
    curr_retriever = initialize_retriever()
    if curr_retriever:
        try:
            nodes = curr_retriever.retrieve(message)
            if nodes:
                res = "⚠️ **[Information Retrieved]** (I encountered a technical glitch, but here is the raw documentation):\n\n"
                for i, node in enumerate(nodes):
                    text = node.get_content() if hasattr(node, "get_content") else str(node)
                    res += f"**Record {i+1}:**\n{text}\n\n"
                return res
            return "I couldn't find any specific records for your query."
        except Exception:
            return "❌ System Error: University records are currently unreachable."
    
    return "I'm sorry, the university search system is offline."
