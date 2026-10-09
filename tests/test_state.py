import pytest
from server.domain.states import (
    SessionState,
    SessionEvent,
    ItemState,
    ItemEvent,
    InvalidTransition,
    transition_session,
    transition_item,
)


@pytest.mark.parametrize(
    "start_state,event,expected_state",
    [
        (SessionState.IDLE, SessionEvent.START, SessionState.ACTIVE),
        (SessionState.IDLE, SessionEvent.PREPARE, SessionState.PREPARING),
        (SessionState.PREPARING, SessionEvent.ACTIVATE, SessionState.ACTIVE),
        (SessionState.ACTIVE, SessionEvent.PAUSE, SessionState.PAUSED),
        (SessionState.PAUSED, SessionEvent.RESUME, SessionState.ACTIVE),
        (SessionState.ACTIVE, SessionEvent.COMPLETE, SessionState.COMPLETED),
        (SessionState.PAUSED, SessionEvent.COMPLETE, SessionState.COMPLETED),
        (SessionState.ACTIVE, SessionEvent.INVALIDATE, SessionState.INVALIDATED),
        (SessionState.PAUSED, SessionEvent.INVALIDATE, SessionState.INVALIDATED),
    ],
)
def test_valid_session_transitions(start_state, event, expected_state):
    result = transition_session(start_state, event)
    assert result == expected_state


@pytest.mark.parametrize(
    "start_state,event",
    [
        (SessionState.IDLE, SessionEvent.PAUSE),
        (SessionState.IDLE, SessionEvent.RESUME),
        (SessionState.IDLE, SessionEvent.COMPLETE),
        (SessionState.ACTIVE, SessionEvent.START),
        (SessionState.ACTIVE, SessionEvent.RESUME),
        (SessionState.PAUSED, SessionEvent.START),
        (SessionState.PAUSED, SessionEvent.PAUSE),
        (SessionState.COMPLETED, SessionEvent.START),
        (SessionState.COMPLETED, SessionEvent.RESUME),
        (SessionState.COMPLETED, SessionEvent.PAUSE),
        (SessionState.INVALIDATED, SessionEvent.START),
        (SessionState.INVALIDATED, SessionEvent.RESUME),
    ],
)
def test_invalid_session_transitions(start_state, event):
    with pytest.raises(InvalidTransition):
        transition_session(start_state, event)


@pytest.mark.parametrize(
    "start_state,event,expected_state",
    [
        (ItemState.LOCKED, ItemEvent.UNLOCK, ItemState.AVAILABLE),
        (ItemState.LOCKED, ItemEvent.EXPIRE, ItemState.EXPIRED),
        (ItemState.AVAILABLE, ItemEvent.COLLECT, ItemState.COLLECTED),
        (ItemState.AVAILABLE, ItemEvent.EXPIRE, ItemState.EXPIRED),
    ],
)
def test_valid_item_transitions(start_state, event, expected_state):
    result = transition_item(start_state, event)
    assert result == expected_state


@pytest.mark.parametrize(
    "start_state,event",
    [
        (ItemState.LOCKED, ItemEvent.COLLECT),
        (ItemState.COLLECTED, ItemEvent.COLLECT),
        (ItemState.COLLECTED, ItemEvent.UNLOCK),
        (ItemState.EXPIRED, ItemEvent.UNLOCK),
        (ItemState.EXPIRED, ItemEvent.COLLECT),
    ],
)
def test_invalid_item_transitions(start_state, event):
    with pytest.raises(InvalidTransition):
        transition_item(start_state, event)
