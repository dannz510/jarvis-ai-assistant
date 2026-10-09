"""Explicit lifecycle states and a small thread-safe event bus for ASTRA."""

from dataclasses import dataclass
from enum import Enum
import threading
import time
from typing import Callable


class AgentState(str, Enum):
    IDLE = "idle"
    LISTENING = "listening"
    PROCESSING = "processing"
    THINKING = "thinking"
    TOOL_SELECTION = "tool_selection"
    EXECUTING = "executing"
    OBSERVING = "observing"
    RESPONDING = "responding"
    INTERRUPTED = "interrupted"
    WAITING_FOR_CLARIFICATION = "waiting_for_clarification"
    COMPLETED = "completed"
    ERROR = "error"


@dataclass(frozen=True)
class AgentEvent:
    name: str
    state: AgentState
    detail: str = ""
    timestamp: float = 0.0


class EventBus:
    """Synchronous event dispatch; subscribers should enqueue UI work themselves."""

    def __init__(self):
        self._lock = threading.RLock()
        self._subscribers = {}
        self._next_token = 0

    def subscribe(self, callback: Callable[[AgentEvent], None]):
        with self._lock:
            self._next_token += 1
            token = self._next_token
            self._subscribers[token] = callback
            return token

    def unsubscribe(self, token):
        with self._lock:
            self._subscribers.pop(token, None)

    def publish(self, event: AgentEvent):
        with self._lock:
            subscribers = tuple(self._subscribers.values())
        for callback in subscribers:
            try:
                callback(event)
            except Exception:
                # Observers must not break inference or tool execution.
                continue


class AgentStateMachine:
    """Validate observable agent transitions and publish state events."""

    _ALLOWED = {
        AgentState.IDLE: {AgentState.LISTENING, AgentState.PROCESSING, AgentState.ERROR},
        AgentState.LISTENING: {AgentState.PROCESSING, AgentState.INTERRUPTED, AgentState.IDLE, AgentState.ERROR},
        AgentState.PROCESSING: {AgentState.THINKING, AgentState.WAITING_FOR_CLARIFICATION, AgentState.ERROR},
        AgentState.THINKING: {AgentState.TOOL_SELECTION, AgentState.RESPONDING, AgentState.WAITING_FOR_CLARIFICATION, AgentState.ERROR},
        AgentState.TOOL_SELECTION: {AgentState.EXECUTING, AgentState.RESPONDING, AgentState.ERROR},
        AgentState.EXECUTING: {AgentState.OBSERVING, AgentState.ERROR, AgentState.INTERRUPTED},
        AgentState.OBSERVING: {AgentState.TOOL_SELECTION, AgentState.RESPONDING, AgentState.ERROR},
        AgentState.RESPONDING: {AgentState.COMPLETED, AgentState.INTERRUPTED, AgentState.ERROR},
        AgentState.INTERRUPTED: {AgentState.LISTENING, AgentState.PROCESSING, AgentState.IDLE},
        AgentState.WAITING_FOR_CLARIFICATION: {AgentState.LISTENING, AgentState.PROCESSING, AgentState.ERROR},
        AgentState.COMPLETED: {AgentState.IDLE, AgentState.LISTENING, AgentState.PROCESSING},
        AgentState.ERROR: {AgentState.IDLE, AgentState.LISTENING, AgentState.PROCESSING},
    }

    def __init__(self, event_bus=None):
        self.event_bus = event_bus or EventBus()
        self._lock = threading.RLock()
        self._state = AgentState.IDLE

    @property
    def state(self):
        with self._lock:
            return self._state

    def transition(self, target, detail=""):
        target = AgentState(target)
        with self._lock:
            if target != self._state and target not in self._ALLOWED[self._state]:
                raise ValueError(f"Invalid ASTRA state transition: {self._state.value} -> {target.value}")
            self._state = target
        self.event_bus.publish(AgentEvent("state_changed", target, detail, time.time()))
        return target
