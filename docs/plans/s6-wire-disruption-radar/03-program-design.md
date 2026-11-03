# Program Design: S6 — Wire disruption radar into global_oracle

## Call Stack Trace

Execution Call Stack Trace:
└── [Project] Autonomous Supply Chain Agent (Root / LangGraph Workflow)
    ├── [Configuration/Env] META_API_KEY, META_API_BASE_URL, META_MODEL_NAME=muse-spark-1.3
    └── [Folder] . (Root module)
        └── [File] graph.py
            └── [Class] AgentState (TypedDict state container)
                └── [Method] global_oracle(state: AgentState) -> Dict[str, Any]
                    ├── [Variable State Shift] Inbound Param: state.get("messages", []) -> list(messages)
                    ├── [Method] disruption_radar.fetch_disruption_alert() -> Dict[str, Any]
                    │   └── [File] disruption_radar.py
                    │       └── [Method] _fetch_feed_headlines(url, limit=5) -> List[str]
                    │       └── [Method] ChatOpenAI.invoke(...) -> AIMessage
                    │       └── [Variable State Shift] Return: {"alert": bool, "severity": str, "summary": str}
                    ├── [Variable State Shift] If alert is True: messages.append(AIMessage(content=f"[GLOBAL ORACLE ALERT] ({severity.upper()}): {summary}"))
                    ├── [Variable State Shift] If alert is False: messages remains unchanged
                    └── [Variable State Shift] Return: {"messages": messages}

## Files
- `graph.py`: Update `global_oracle` node to invoke `fetch_disruption_alert` and format `AIMessage` accordingly.
- `tests/test_global_oracle_integration.py`: Integration test verifying `global_oracle` calling `disruption_radar.fetch_disruption_alert`.

## Types & signatures
```python
def global_oracle(state: AgentState) -> Dict[str, List[BaseMessage]]:
    ...
```

## Test Plan
- `test_global_oracle_integration_live`: Runs `global_oracle` with real network / Meta API (skips if `META_API_KEY` is not present), asserts messages either unchanged (alert=False) or contains `[GLOBAL ORACLE ALERT]`.
- `test_global_oracle_integration_with_alert`: Mocks `fetch_disruption_alert` to return `{"alert": True, "severity": "high", "summary": "Port congestion at Long Beach"}`, asserts message appended matches `[GLOBAL ORACLE ALERT] (HIGH): Port congestion at Long Beach`.
- `test_global_oracle_integration_silent_no_alert`: Mocks `fetch_disruption_alert` returning `{"alert": False, "severity": "low", "summary": "No active disruptions detected."}`, asserts messages list is identical/unchanged.
