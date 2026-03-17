import logging
import asyncio
from llama_index.core.llms import ChatMessage, MessageRole

logger = logging.getLogger(__name__)

class PlannerAgent:
    """Decides if the query requires LPU documentation retrieval."""
    def __init__(self, llm):
        self.llm = llm

    async def decide_strategy(self, query):
        prompt = f"""
        You are an LPU University Assistant Planner. 
        Decide if the user's query requires specific university documentation (rules, courses, fees, dates) 
        or if it's a general greeting/conversation.

        Query: {query}

        Answer ONLY with one word: RETRIEVE or DIRECT
        """
        try:
            response = await self.llm.acomplete(prompt)
            decision = str(response).strip().upper()
            if "RETRIEVE" in decision:
                return "RETRIEVE"
            return "DIRECT"
        except Exception as e:
            logger.error(f"Planner Error: {e}")
            return "RETRIEVE"  # Safety fallback

class RetrieverAgent:
    """Fetches relevant context from LPU Knowledge Base."""
    def __init__(self, retriever):
        self.retriever = retriever

    async def fetch_context(self, query):
        if not self.retriever:
            return None
        try:
            # Note: AmazonKnowledgeBasesRetriever.retrieve is generally synchronous in LlamaIndex
            # We wrap it or just call it if it's not truly async in this version
            nodes = self.retriever.retrieve(query)
            context = "\n".join([n.get_content() if hasattr(n, "get_content") else str(n) for n in nodes])
            return context
        except Exception as e:
            logger.error(f"Retriever Error: {e}")
            return None

class GeneratorAgent:
    """Generates the final response based on query and context."""
    def __init__(self, llm):
        self.llm = llm

    async def generate_response(self, query, context, chat_history_objs):
        if context:
            system_content = f"""
            You are a helpful LPU University Assistant. Answer the user's query based ONLY on the provided context.
            If the context doesn't have the answer, say you don't know rather than making it up.

            Context:
            {context}
            """
        else:
            system_content = "You are a helpful LPU University Assistant. Answer the user's query directly."

        try:
            # Construct message list: History + System Prompt (as user for simplicity in some LLM wrappers) + Current Query
            # Actually, most ChatLLMs prefer System, then History, then User.
            messages = [ChatMessage(role=MessageRole.SYSTEM, content=system_content)] + chat_history_objs + [ChatMessage(role=MessageRole.USER, content=query)]
            response = await self.llm.achat(messages)
            return str(response)
        except Exception as e:
            logger.error(f"Generator Error: {e}")
            return "I apologize, but I encountered an error generating a response."

class Orchestrator:
    """Coordinates the multi-agent workflow."""
    def __init__(self, llm, retriever):
        self.planner = PlannerAgent(llm)
        self.retriever = RetrieverAgent(retriever)
        self.generator = GeneratorAgent(llm)
        self.llm = llm

    async def handle_query(self, query, chat_history_objs):
        print(f"\n[Orchestrator] Starting workflow for: '{query}'")
        
        # Phase 1: Planning
        decision = await self.planner.decide_strategy(query)
        print(f"[Planner] Decision: {decision}")

        context = None
        if decision == "RETRIEVE":
            # Phase 2: Retrieval
            context = await self.retriever.fetch_context(query)
            context_len = len(context) if context else 0
            print(f"[Retriever] Context length: {context_len} chars")
            
            # Phase 2.5: Fallback validation
            if context_len < 50:
                print("[Retriever] Low confidence context found.")
        
        # Phase 3: Generation
        response = await self.generator.generate_response(query, context, chat_history_objs)
        print(f"[Generator] Response generated ({len(response)} chars)")
        
        return response
