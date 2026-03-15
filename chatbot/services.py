import os
import logging
import traceback
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

logger = logging.getLogger(__name__)

# Global variables to hold initialized components
retriever = None
agent = None
HAS_LLAMA = False

try:
    from llama_index.retrievers.bedrock import AmazonKnowledgeBasesRetriever
    from llama_index.llms.openai import OpenAI
    from llama_index.core.query_engine import RetrieverQueryEngine
    from llama_index.core.tools import QueryEngineTool
    from llama_index.core import Settings
    from llama_index.core.llms import ChatMessage, MessageRole
    
    try:
        from llama_index.core.agent import ReActAgent
    except Exception:
        try:
            from llama_index.core.agent.react.base import ReActAgent
        except Exception:
            ReActAgent = None
            
    HAS_LLAMA = True
except ImportError as e:
    HAS_LLAMA = False
    logger.error(f"LlamaIndex or dependencies not found: {e}")

def initialize_retriever():
    """Initializes only the retriever (more stable than the agent)."""
    global retriever
    if retriever is not None:
        return retriever
    try:
        aws_region = os.getenv("AWS_REGION") or os.getenv("AWS_DEFAULT_REGION") or "ap-south-1"
        kb_id = os.getenv("BEDROCK_KNOWLEDGE_BASE_ID")
        if kb_id:
            retriever = AmazonKnowledgeBasesRetriever(
                knowledge_base_id=kb_id,
                retrieval_config={"vectorSearchConfiguration": {"numberOfResults": 3}},
                region_name=aws_region
            )
        return retriever
    except Exception as e:
        logger.error(f"Failed to initialize retriever: {e}")
        return None

def initialize_agent():
    """Initializes the AI agent. If this fails, we fall back to retriever later."""
    global agent, retriever
    if agent is not None:
        return agent
    
    try:
        github_token = os.getenv("GITHUB_TOKEN")
        github_model = os.getenv("GITHUB_MODEL", "gpt-4o")
        
        # Ensure retriever is ready
        curr_retriever = initialize_retriever()
        if not curr_retriever or not github_token:
            return None

        # Initialize LLM
        llm = OpenAI(
            model=github_model,
            api_key=github_token,
            api_base="https://models.github.ai/inference"
        )
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
            
            # Use most compatible method based on library version
            try:
                # 1. Try from_tools (common in modern llama-index)
                if hasattr(ReActAgent, 'from_tools'):
                    logger.info("Initializing ReActAgent via from_tools")
                    agent = ReActAgent.from_tools(
                        tools=[_knowledge_base_tool],
                        llm=llm,
                        context="You are a helpful AI assistant for LPU."
                    )
                # 2. Try from_llm_and_tools (found in some versions)
                elif hasattr(ReActAgent, 'from_llm_and_tools'):
                    logger.info("Initializing ReActAgent via from_llm_and_tools")
                    agent = ReActAgent.from_llm_and_tools(
                        tools=[_knowledge_base_tool],
                        llm=llm,
                        context="You are a helpful AI assistant for LPU."
                    )
                # 3. Direct constructor (Legacy or specific versions)
                else:
                    logger.info("Initializing ReActAgent via direct constructor")
                    agent = ReActAgent(
                        tools=[_knowledge_base_tool],
                        llm=llm,
                        context="You are a helpful AI assistant for LPU."
                    )
            except Exception as e:
                # 4. Final desperate fallback - sometimes from_tools exists but fails for other reasons
                logger.warning(f"Preferred initialization failed: {e}. Trying direct instantiation as fallback.")
                try:
                    agent = ReActAgent(
                        tools=[_knowledge_base_tool],
                        llm=llm,
                        context="You are a helpful AI assistant for LPU."
                    )
                except Exception as final_e:
                    logger.error(f"All ReActAgent initialization attempts failed: {final_e}")
                    raise final_e
        else:
            # Simple wrapper
            class SimpleAgent:
                def __init__(self, qe): self.qe = qe
                async def achat(self, m, chat_history=None): return await self.qe.aquery(m)
            agent = SimpleAgent(query_engine)
            
        return agent
    except Exception as e:
        logger.error(f"Agent initialization error (will use raw data instead): {e}")
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
            
            if hasattr(curr_agent, 'achat'):
                response = await curr_agent.achat(message, chat_history=chat_history_objs)
                return str(response)
            else:
                response = await curr_agent.aquery(message)
                return str(response)
        except Exception as e:
            logger.error(f"Agent execution failed: {e}")
            # Do not return, fall through to raw data
    
    # AGGRESSIVE FALLBACK: If Agent fails or LLM is down, return raw chunks
    curr_retriever = initialize_retriever()
    if curr_retriever:
        try:
            nodes = curr_retriever.retrieve(message)
            if nodes:
                res = "⚠️ **[Information Retrieved]** (I'm having trouble thinking right now, but here is what the records say):\n\n"
                for i, node in enumerate(nodes):
                    text = node.get_content() if hasattr(node, "get_content") else str(node)
                    res += f"**Record {i+1}:**\n{text}\n\n"
                return res
            else:
                return "I couldn't find any specific records for your query. Please try rephrasing."
        except Exception as re:
            return f"❌ System Error: Connection to database failed ({str(re)})."
    
    return "I'm sorry, the university search system is currently unreachable. Please check back later."
