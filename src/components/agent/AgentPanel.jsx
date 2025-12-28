import React, { useState, useEffect, useCallback } from "react";
import { apiGet, apiPost } from "../../services/api";
import "./AgentPanel.css";

function AgentPanel() {
  const [status, setStatus] = useState(null);
  const [loading, setLoading] = useState(true);
  const [actionLoading, setActionLoading] = useState(null);
  const [message, setMessage] = useState(null);
  const [vramMode, setVramMode] = useState("low");
  const [actionLog, setActionLog] = useState([]);

  const fetchStatus = useCallback(async () => {
    try {
      const res = await apiGet("/api/v1/agent/status");
      const data = await res.json();
      setStatus(data);
    } catch (e) {
      setStatus({ status: "error", error: e.message });
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchStatus();
    const interval = setInterval(fetchStatus, 10000);
    return () => clearInterval(interval);
  }, [fetchStatus]);

  const executeAction = async (actionId, params = {}, successMsg) => {
    setActionLoading(actionId);
    setMessage(null);

    try {
      const res = await apiPost("/api/v1/agent/action", {
        action: actionId,
        parameters: params,
        force: true,
      });
      const data = await res.json();

      const logEntry = {
        time: new Date().toLocaleTimeString(),
        action: actionId,
        success: data.success,
        message: data.message || data.error,
      };
      setActionLog((prev) => [logEntry, ...prev.slice(0, 19)]);

      if (data.success) {
        setMessage({ type: "success", text: successMsg || data.message || "Action completed" });
        fetchStatus();
      } else if (data.requires_approval) {
        setMessage({ type: "warning", text: `Action requires approval: ${data.message}` });
      } else {
        setMessage({ type: "error", text: data.error || "Action failed" });
      }
    } catch (e) {
      setMessage({ type: "error", text: e.message });
      setActionLog((prev) => [
        { time: new Date().toLocaleTimeString(), action: actionId, success: false, message: e.message },
        ...prev.slice(0, 19),
      ]);
    } finally {
      setActionLoading(null);
    }
  };

  const handleStartSD = () => {
    executeAction("start_sd", { vram_mode: vramMode }, `Starting Stable Diffusion (${vramMode} VRAM mode)`);
  };

  const handleStopSD = () => {
    executeAction("stop_sd", {}, "Stopping Stable Diffusion");
  };

  const handleRefreshResources = () => {
    executeAction("get_resources", {}, "Resources refreshed");
  };

  const getResourceLevel = (percentage) => {
    if (percentage < 50) return "low";
    if (percentage < 80) return "medium";
    return "high";
  };

  if (loading) {
    return (
      <div className="panel agent-panel">
        <div className="agent-loading">Loading agent status...</div>
      </div>
    );
  }

  if (status?.status === "disabled") {
    return (
      <div className="panel agent-panel">
        <div className="agent-header">
          <h2>Agent Control</h2>
          <div className="agent-status-badge disabled">
            <span className="agent-status-dot disabled"></span>
            Disabled
          </div>
        </div>
        <div className="agent-disabled">
          <div className="agent-disabled-text">
            The ARES Agent is not configured or disabled.
          </div>
          <div className="agent-disabled-text" style={{ fontSize: "0.9em", opacity: 0.7 }}>
            Configure the agent URL and API key in Settings to enable remote control of your 4090 rig.
          </div>
        </div>
      </div>
    );
  }

  const isOnline = status?.status === "online";
  const resources = status?.resources || {};
  const services = status?.services || {};

  return (
    <div className="panel agent-panel">
      <div className="agent-header">
        <h2>Agent Control</h2>
        <div className={`agent-status-badge ${isOnline ? "online" : "offline"}`}>
          <span className={`agent-status-dot ${isOnline ? "online" : "offline"}`}></span>
          {isOnline ? "Online" : "Offline"}
        </div>
      </div>

      {message && (
        <div className={`agent-message ${message.type}`}>
          {message.text}
        </div>
      )}

      <div className="agent-content">
        {!isOnline ? (
          <div className="agent-message error">
            Cannot connect to agent: {status?.error || "Unknown error"}
          </div>
        ) : (
          <>
            {/* System Resources */}
            <div className="agent-section">
              <h3>System Resources</h3>
              <div className="agent-resources">
                {resources.gpu_memory_used !== undefined && (
                  <div className="resource-item">
                    <div className="resource-label">
                      <span>GPU Memory</span>
                      <span className="resource-value">
                        {resources.gpu_memory_used} / {resources.gpu_memory_total} MB
                      </span>
                    </div>
                    <div className="resource-bar">
                      <div
                        className={`resource-fill ${getResourceLevel(resources.gpu_memory_percent || 0)}`}
                        style={{ width: `${resources.gpu_memory_percent || 0}%` }}
                      ></div>
                    </div>
                  </div>
                )}
                {resources.cpu_percent !== undefined && (
                  <div className="resource-item">
                    <div className="resource-label">
                      <span>CPU Usage</span>
                      <span className="resource-value">{resources.cpu_percent}%</span>
                    </div>
                    <div className="resource-bar">
                      <div
                        className={`resource-fill ${getResourceLevel(resources.cpu_percent)}`}
                        style={{ width: `${resources.cpu_percent}%` }}
                      ></div>
                    </div>
                  </div>
                )}
                {resources.ram_percent !== undefined && (
                  <div className="resource-item">
                    <div className="resource-label">
                      <span>RAM Usage</span>
                      <span className="resource-value">{resources.ram_percent}%</span>
                    </div>
                    <div className="resource-bar">
                      <div
                        className={`resource-fill ${getResourceLevel(resources.ram_percent)}`}
                        style={{ width: `${resources.ram_percent}%` }}
                      ></div>
                    </div>
                  </div>
                )}
              </div>
              <div style={{ marginTop: "12px" }}>
                <button
                  className="agent-btn"
                  onClick={handleRefreshResources}
                  disabled={actionLoading}
                >
                  Refresh
                </button>
              </div>
            </div>

            {/* Services */}
            <div className="agent-section">
              <h3>Services</h3>
              <div className="agent-services">
                {/* Stable Diffusion */}
                <div className="service-card">
                  <div className="service-header">
                    <span className="service-name">Stable Diffusion</span>
                    <span className={`service-status ${services.sd?.running ? "running" : "stopped"}`}>
                      {services.sd?.running ? "Running" : "Stopped"}
                    </span>
                  </div>
                  <div className="service-actions">
                    {!services.sd?.running ? (
                      <>
                        <div className="vram-selector">
                          <label>VRAM:</label>
                          <select value={vramMode} onChange={(e) => setVramMode(e.target.value)}>
                            <option value="low">Low (~4GB)</option>
                            <option value="medium">Medium (~8GB)</option>
                            <option value="full">Full (~12GB)</option>
                          </select>
                        </div>
                        <button
                          className="agent-btn success"
                          onClick={handleStartSD}
                          disabled={actionLoading === "start_sd"}
                        >
                          {actionLoading === "start_sd" ? "Starting..." : "Start"}
                        </button>
                      </>
                    ) : (
                      <button
                        className="agent-btn danger"
                        onClick={handleStopSD}
                        disabled={actionLoading === "stop_sd"}
                      >
                        {actionLoading === "stop_sd" ? "Stopping..." : "Stop"}
                      </button>
                    )}
                  </div>
                </div>

                {/* Ollama */}
                <div className="service-card">
                  <div className="service-header">
                    <span className="service-name">Ollama</span>
                    <span className={`service-status ${services.ollama?.running ? "running" : "stopped"}`}>
                      {services.ollama?.running ? "Running" : "Stopped"}
                    </span>
                  </div>
                  <div className="service-actions">
                    {!services.ollama?.running ? (
                      <button
                        className="agent-btn success"
                        onClick={() => executeAction("start_ollama", {}, "Starting Ollama")}
                        disabled={actionLoading === "start_ollama"}
                      >
                        {actionLoading === "start_ollama" ? "Starting..." : "Start"}
                      </button>
                    ) : (
                      <button
                        className="agent-btn danger"
                        onClick={() => executeAction("stop_ollama", {}, "Stopping Ollama")}
                        disabled={actionLoading === "stop_ollama"}
                      >
                        {actionLoading === "stop_ollama" ? "Stopping..." : "Stop"}
                      </button>
                    )}
                  </div>
                </div>
              </div>
            </div>

            {/* Action Log */}
            {actionLog.length > 0 && (
              <div className="agent-section">
                <h3>Recent Actions</h3>
                <div className="agent-log">
                  {actionLog.map((entry, idx) => (
                    <div key={idx} className="log-entry">
                      <span className="log-time">{entry.time}</span>
                      <span className="log-action">{entry.action}</span>
                      <span className={`log-result ${entry.success ? "success" : "error"}`}>
                        {entry.success ? "OK" : "FAIL"}: {entry.message}
                      </span>
                    </div>
                  ))}
                </div>
              </div>
            )}
          </>
        )}
      </div>
    </div>
  );
}

export default AgentPanel;

