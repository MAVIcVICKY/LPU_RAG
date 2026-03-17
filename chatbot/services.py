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
agent = None
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
    """Initializes the AI agent. If this fails, we fall back to retriever later."""
    global agent, retriever
    if agent is not None:
        return agent
    
    if not HAS_LLAMA:
        logger.error("Cannot initialize agent: LlamaIndex missing.")
        return None

    try:
        # Configuration retrieval
        github_token = get_config("GITHUB_TOKEN", "/rag-app/github-token")
        github_model = get_config("GITHUB_MODEL", "/rag-app/github-model") or "gpt-4o"
        bedrock_model = get_config("BEDROCK_MODEL_ID", "/rag-app/model-id")
        aws_region = os.getenv("AWS_REGION") or os.getenv("AWS_DEFAULT_REGION") or "ap-south-1"
        
        # Ensure retriever is ready
        curr_retriever = initialize_retriever()
        if not curr_retriever:
            logger.warning("Retriever not initialized; raw data fallback will be used.")
            return None

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

        # Create Query Engine
        query_engine = RetrieverQueryEngine.from_args(
            retriever=curr_retriever,
            llm=llm
        )

        # Create Agent
        if ReActAgent:
            _knowledge_base_tool = QueryEngineTool.from_defaults(
                query_engine=query_engine,
                name="lpu_kb",
                description="Information about LPU University rules and courses.",
            )
            
            # Try multiple initialization patterns
            try:
                if hasattr(ReActAgent, 'from_tools'):
                    agent = ReActAgent.from_tools(tools=[_knowledge_base_tool], llm=llm, context="You are a helpful AI assistant for LPU.")
                elif hasattr(ReActAgent, 'from_llm_and_tools'):
                    agent = ReActAgent.from_llm_and_tools(tools=[_knowledge_base_tool], llm=llm, context="You are a helpful AI assistant for LPU.")
                else:
                    agent = ReActAgent(tools=[_knowledge_base_tool], llm=llm, context="You are a helpful AI assistant for LPU.")
            except Exception as e:
                logger.warning(f"Preferred ReActAgent init failed: {e}. Falling back to direct instantiation.")
                agent = ReActAgent(tools=[_knowledge_base_tool], llm=llm, context="You are a helpful AI assistant for LPU.")
        else:
            class SimpleAgent:
                def __init__(self, qe): self.qe = qe
                async def achat(self, m, chat_history=None): return await self.qe.aquery(m)
            agent = SimpleAgent(query_engine)
            
        return agent
    except Exception as e:
        logger.error(f"Agent initialization error: {e}")
        return None

async def get_agent_response(message, chat_history):
    # Try fully initialized Agent first
    curr_agent = initialize_agent()
    if curr_agent:
        try:
            chat_history_objs = []
            for msg in chat_history:
                role = MessageRole.USER if msg["role"] == "user" else MessageRole.ASSISTANT
                chat_history_objs.append(ChatMessage(role=role, content=msg["content"]))
            
            # Multi-method dispatch with aggressive resolution loop
            response = None
            if hasattr(curr_agent, 'achat'):
                logger.info("Trying agent.achat...")
                response = curr_agent.achat(message, chat_history=chat_history_objs)
            elif hasattr(curr_agent, 'arun'):
                logger.info("Trying agent.arun with history...")
                # Note: Workflow-based agents often take chat_history
                response = curr_agent.arun(user_msg=message, chat_history=chat_history_objs)
            elif hasattr(curr_agent, 'chat'):
                logger.info("Trying agent.chat...")
                response = curr_agent.chat(message, chat_history=chat_history_objs)
            elif hasattr(curr_agent, 'run'):
                logger.info("Trying agent.run with history...")
                response = curr_agent.run(user_msg=message, chat_history=chat_history_objs)
            elif hasattr(curr_agent, 'aquery'):
                logger.info("Trying agent.aquery (history may be ignored)...")
                response = curr_agent.aquery(message)
            elif hasattr(curr_agent, 'query'):
                logger.info("Trying agent.query (history may be ignored)...")
                response = curr_agent.query(message)
            
            # Agressively resolve any awaitables or WorkflowHandlers
            # We do this in a loop because some methods return a coroutine that returns a handler
            # which then needs to be awaited itself to get the final result.
            for attempt in range(5):
                if response is None:
                    break
                
                res_type = str(type(response))
                logger.info(f"Resolution Attempt {attempt+1}: Type is {res_type}")
                
                if inspect.isawaitable(response):
                    logger.debug("Awaiting coroutine/awaitable...")
                    response = await response
                elif 'WorkflowHandler' in res_type:
                    logger.debug("Awaiting WorkflowHandler...")
                    response = await response
                else:
                    # We reached a final result (likely a Response object or string)
                    break

            if response is not None:
                final_answer = str(response)
                logger.info(f"Successfully resolved response: {final_answer[:50]}...")
                return final_answer
            
            logger.error(f"No valid query methods found on agent type: {type(curr_agent)}")
        except Exception as e:
            logger.error(f"Agent execution failed: {e}")
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
