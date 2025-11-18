from typing import AsyncIterator

from agno.run.agent import RunOutput, RunStartedEvent, RunContentEvent, IntermediateRunContentEvent, \
    RunContentCompletedEvent, RunCompletedEvent, RunErrorEvent, RunCancelledEvent, RunPausedEvent, RunContinuedEvent, \
    PreHookStartedEvent, PreHookCompletedEvent, PostHookStartedEvent, PostHookCompletedEvent, ReasoningStartedEvent, \
    ReasoningStepEvent, ReasoningCompletedEvent, MemoryUpdateStartedEvent, MemoryUpdateCompletedEvent, \
    SessionSummaryStartedEvent, SessionSummaryCompletedEvent, ToolCallStartedEvent, ToolCallCompletedEvent, \
    ParserModelResponseStartedEvent, ParserModelResponseCompletedEvent, OutputModelResponseStartedEvent, \
    OutputModelResponseCompletedEvent, CustomEvent

from src.agno.agents.MemoryAgent import memory_agent
from src.agno.agents.SecretaryAgent import SecretaryAgent


def run_request(user_id: str, session_id: str, message: str) -> AsyncIterator[
    RunStartedEvent | RunContentEvent | IntermediateRunContentEvent | RunContentCompletedEvent | RunCompletedEvent | RunErrorEvent | RunCancelledEvent | RunPausedEvent | RunContinuedEvent | PreHookStartedEvent | PreHookCompletedEvent | PostHookStartedEvent | PostHookCompletedEvent | ReasoningStartedEvent | ReasoningStepEvent | ReasoningCompletedEvent | MemoryUpdateStartedEvent | MemoryUpdateCompletedEvent | SessionSummaryStartedEvent | SessionSummaryCompletedEvent | ToolCallStartedEvent | ToolCallCompletedEvent | ParserModelResponseStartedEvent | ParserModelResponseCompletedEvent | OutputModelResponseStartedEvent | OutputModelResponseCompletedEvent | CustomEvent | RunOutput
]:
    return SecretaryAgent(user_id=user_id, session_ts=session_id).arun(f"{user_id}: {message}", stream=True, stream_events=True)


async def recall_preferences(user_id: str) -> dict[str, str]:
    memories = await memory_agent.aget_user_memories(user_id=user_id)
    return {memory.memory_id: memory.memory for memory in reversed(memories)}


def forget_preference(user_id: str, preference_id: str) -> None:
    memory_agent.delete_user_memory(preference_id, user_id=user_id)
