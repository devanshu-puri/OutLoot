from enum import Enum
from typing import Dict, Set


class SessionState(str, Enum):
    IDLE = "IDLE"
    PREPARING = "PREPARING"
    ACTIVE = "ACTIVE"
    PAUSED = "PAUSED"
    COMPLETED = "COMPLETED"
    INVALIDATED = "INVALIDATED"


class SessionEvent(str, Enum):
    START = "START"
    PREPARE = "PREPARE"
    ACTIVATE = "ACTIVATE"
    PAUSE = "PAUSE"
    RESUME = "RESUME"
    COMPLETE = "COMPLETE"
    INVALIDATE = "INVALIDATE"


class ItemState(str, Enum):
    LOCKED = "LOCKED"
    AVAILABLE = "AVAILABLE"
    COLLECTED = "COLLECTED"
    EXPIRED = "EXPIRED"


class ItemEvent(str, Enum):
    UNLOCK = "UNLOCK"
    COLLECT = "COLLECT"
    EXPIRE = "EXPIRE"


class InvalidTransition(Exception):
    def __init__(self, current_state: str, event: str):
        super().__init__(f"Invalid transition from state '{current_state}' on event '{event}'")
        self.current_state = current_state
        self.event = event


# Transition table for Session: (CurrentState, Event) -> NewState
SESSION_TRANSITIONS: Dict[SessionState, Dict[SessionEvent, SessionState]] = {
    SessionState.IDLE: {
        SessionEvent.START: SessionState.ACTIVE,
        SessionEvent.PREPARE: SessionState.PREPARING,
        SessionEvent.ACTIVATE: SessionState.ACTIVE,
    },
    SessionState.PREPARING: {
        SessionEvent.ACTIVATE: SessionState.ACTIVE,
        SessionEvent.START: SessionState.ACTIVE,
        SessionEvent.INVALIDATE: SessionState.INVALIDATED,
    },
    SessionState.ACTIVE: {
        SessionEvent.PAUSE: SessionState.PAUSED,
        SessionEvent.COMPLETE: SessionState.COMPLETED,
        SessionEvent.INVALIDATE: SessionState.INVALIDATED,
    },
    SessionState.PAUSED: {
        SessionEvent.RESUME: SessionState.ACTIVE,
        SessionEvent.COMPLETE: SessionState.COMPLETED,
        SessionEvent.INVALIDATE: SessionState.INVALIDATED,
    },
    # COMPLETED and INVALIDATED are terminal states
    SessionState.COMPLETED: {},
    SessionState.INVALIDATED: {},
}


def transition_session(current: SessionState, event: SessionEvent) -> SessionState:
    if current not in SESSION_TRANSITIONS or event not in SESSION_TRANSITIONS[current]:
        raise InvalidTransition(current.value, event.value)
    return SESSION_TRANSITIONS[current][event]


# Transition table for SpawnedItem
ITEM_TRANSITIONS: Dict[ItemState, Dict[ItemEvent, ItemState]] = {
    ItemState.LOCKED: {
        ItemEvent.UNLOCK: ItemState.AVAILABLE,
        ItemEvent.EXPIRE: ItemState.EXPIRED,
    },
    ItemState.AVAILABLE: {
        ItemEvent.COLLECT: ItemState.COLLECTED,
        ItemEvent.EXPIRE: ItemState.EXPIRED,
    },
    ItemState.COLLECTED: {},
    ItemState.EXPIRED: {},
}


def transition_item(current: ItemState, event: ItemEvent) -> ItemState:
    if current not in ITEM_TRANSITIONS or event not in ITEM_TRANSITIONS[current]:
        raise InvalidTransition(current.value, event.value)
    return ITEM_TRANSITIONS[current][event]
