"""UI navigation states transcribed from the supplied PlantUML diagram.

This module intentionally contains no Qt imports so the transition rules can
be tested independently from the desktop UI.
"""

TRANSITIONS = {
    "W1": {"W0", "W2"},
    # W2 -> W4 is an added return path for the scout after area correction.
    # It is absent from the supplied state diagram but required to avoid a dead end.
    "W2": {"W1", "W3", "W4", "W6"},
    "W3": {"W1", "W2"},
    "W4": {"W2", "W0"},
    "W5": {"W0"},
    "W6": {"W0"},
    "W7": {"W0"},
}

# Saving an inspection is a self-transition W4 -> W4 and does not navigate.
SELF_TRANSITIONS = {"W4"}
LOGOUT_STATES = {"W1", "W4", "W5", "W6", "W7"}

# Role-level window availability is intentionally separate from the global
# state graph; the state diagram itself does not encode actor permissions.
ROLE_STATES = {
    "Агроном": {"W1", "W2", "W3", "W6"},
    "Агроскаут": {"W4", "W2"},
    "Инженер-механизатор": {"W5"},
    "Аналитик": {"W6"},
    "Государственное / экологическое ведомство": {"W7"},
}


def is_transition_allowed(source: str, target: str) -> bool:
    return target in TRANSITIONS.get(source, set()) or (source == target and source in SELF_TRANSITIONS)
