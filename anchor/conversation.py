"""
Conversation module for Anchor CLI.
Handles the discussion phase before code modifications.
"""

from dataclasses import dataclass, field
from typing import List, Dict, Optional
from enum import Enum


class ConversationPhase(Enum):
    """Phases of the conversation flow."""

    DISCUSS = "discuss"
    PLAN = "plan"
    CONFIRM = "confirm"
    EDIT = "edit"
    SAVE = "save"


@dataclass
class Message:
    """A single message in the conversation."""

    role: str  # 'user' or 'assistant'
    content: str
    phase: ConversationPhase


@dataclass
class ConversationBuffer:
    """
    Buffer to hold conversation history and state during the modification process.

    Flow: Prompt -> Discuss (Loop) -> Plan -> Confirmation -> Edit -> Save
    """

    feature_request: str
    context_summary: str = ""
    messages: List[Message] = field(default_factory=list)
    current_phase: ConversationPhase = ConversationPhase.DISCUSS
    implementation_plan: Optional[str] = None
    confirmed: bool = False
    affected_files: List[str] = field(default_factory=list)

    def add_message(
        self, role: str, content: str, phase: Optional[ConversationPhase] = None
    ):
        """Add a message to the conversation history."""
        if phase is None:
            phase = self.current_phase
        self.messages.append(Message(role=role, content=content, phase=phase))

    def get_discussion_history(self) -> str:
        """Get the discussion phase history for context."""
        discussion_msgs = [
            f"{msg.role}: {msg.content}"
            for msg in self.messages
            if msg.phase == ConversationPhase.DISCUSS
        ]
        return "\n".join(discussion_msgs)

    def transition_to(self, phase: ConversationPhase):
        """Transition to a new phase."""
        self.current_phase = phase

    def is_complete(self) -> bool:
        """Check if the conversation has been confirmed."""
        return self.confirmed and self.implementation_plan is not None

    def to_dict(self) -> Dict:
        """Serialize conversation state."""
        return {
            "feature_request": self.feature_request,
            "context_summary": self.context_summary,
            "current_phase": self.current_phase.value,
            "implementation_plan": self.implementation_plan,
            "confirmed": self.confirmed,
            "affected_files": self.affected_files,
            "message_count": len(self.messages),
        }


def create_analysis_prompt(feature: str, repo_context: str) -> str:
    """
    Create the initial prompt for analyzing a feature request.
    """
    return f"""Analyze this request concisely:
Feature Request: {feature}

Context:
{repo_context}

Provide:
1. A 1-sentence summary of what's needed.
2. Direct clarifying questions if needed.
Keep it brief and avoid suggesting new files unless necessary."""


def create_discussion_prompt(
    feature: str, discussion_history: str, user_response: str
) -> str:
    """
    Create a prompt for continuing the discussion.
    """
    return f"""Task: "{feature}"
History:
{discussion_history}
User said: {user_response}

Respond briefly. If you have enough info, say "I have enough information to create a plan."."""


def create_planning_prompt(
    feature: str, full_conversation: str, repo_context: str
) -> str:
    """
    Create a prompt for generating the plan.
    """
    return f"""Create a MINIMAL implementation plan.

Task: {feature}
Discussion: {full_conversation}
Context: {repo_context}

Rules:
1. Only modify files that are absolutely necessary.
2. No new modules/files unless requested.
3. Steps should be a simple bulleted list.
4. Keep the summary under 3 lines."""
