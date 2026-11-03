import os
import pytest
from unittest.mock import patch

def test_record_trace(tmp_path):
    test_db = str(tmp_path / "test_traces.db")
    with patch("agent_tracer.DB_PATH", test_db):
        from agent_tracer import record_trace, get_traces, AgentTrace
        trace = record_trace(
            agent_name="global_oracle",
            tenant_id="tenant_123",
            input_text="Check disruptions in red sea",
            output_text="Red Sea disruption detected",
            decision="PROCEED",
            saving_usd=1500.50,
            latency_ms=120
        )
        assert isinstance(trace, AgentTrace)
        assert trace.agent_name == "global_oracle"
        assert trace.tenant_id == "tenant_123"
        assert trace.decision == "PROCEED"
        assert trace.saving_usd == 1500.50
        assert trace.latency_ms == 120
        assert len(trace.trace_id) > 0
        assert trace.timestamp is not None
        assert trace.input_summary == "Check disruptions in red sea"
        assert trace.output_summary == "Red Sea disruption detected"

        # Assert trace saved and retrievable
        traces = get_traces("tenant_123")
        assert len(traces) == 1
        assert traces[0].trace_id == trace.trace_id
        assert traces[0].saving_usd == 1500.50
        assert traces[0].agent_name == "global_oracle"

def test_agent_stats(tmp_path):
    test_db = str(tmp_path / "test_traces.db")
    with patch("agent_tracer.DB_PATH", test_db):
        from agent_tracer import record_trace, get_agent_stats
        record_trace("global_oracle", "tenant_abc", "in1", "out1", decision="PROCEED", saving_usd=100.0, latency_ms=50)
        record_trace("forecast_demand", "tenant_abc", "in2", "out2", decision="ESCALATE", saving_usd=250.0, latency_ms=100)
        record_trace("a2a_negotiate", "tenant_abc", "in3", "out3", decision="REJECT", saving_usd=50.0, latency_ms=150)
        # Trace for another tenant should not pollute stats
        record_trace("global_oracle", "tenant_xyz", "in4", "out4", decision="PROCEED", saving_usd=999.0, latency_ms=20)

        stats = get_agent_stats("tenant_abc")
        # Assert stats.total_savings_usd == sum of all trace savings
        assert stats["total_actions"] == 3
        assert stats["total_savings_usd"] == 100.0 + 250.0 + 50.0
        assert stats["avg_latency_ms"] == pytest.approx((50 + 100 + 150) / 3, 0.01)
        assert stats["decisions"] == {"PROCEED": 1, "ESCALATE": 1, "REJECT": 1}
        assert "global_oracle" in stats["by_agent"]
        assert stats["by_agent"]["global_oracle"]["count"] == 1
        assert stats["by_agent"]["global_oracle"]["savings"] == 100.0
        assert stats["by_agent"]["forecast_demand"]["count"] == 1
        assert stats["by_agent"]["forecast_demand"]["savings"] == 250.0
        assert stats["by_agent"]["a2a_negotiate"]["count"] == 1
        assert stats["by_agent"]["a2a_negotiate"]["savings"] == 50.0

def test_demo_mode_seed_traces(tmp_path):
    test_db = str(tmp_path / "test_demo_traces.db")
    with patch("agent_tracer.DB_PATH", test_db):
        from agent_tracer import seed_demo_traces, get_traces, get_agent_stats
        seed_demo_traces()
        traces = get_traces("Tenant_A", limit=100)
        assert len(traces) == 20
        stats = get_agent_stats("Tenant_A")
        assert stats["total_actions"] == 20
        assert stats["total_savings_usd"] > 0
        assert stats["decisions"]["PROCEED"] > 0
        assert stats["decisions"]["ESCALATE"] > 0
