import React, { useState, useEffect, useCallback, useRef } from "react";
import { apiGet, apiPost } from "../../services/api";
import "./AgentPanel.css";

const AGENT_POLLING_KEY = 'ares_agent_auto_polling';

function AgentPanel() {
  const [status, setStatus] = useState(null);
  const [loading, setLoading] = useState(true);
  const [checking, setChecking] = useState(false);
  const [actionLoading, setActionLoading] = useState(null);
  const [message, setMessage] = useState(null);
  const [vramMode, setVramMode] = useState("low");
  const [actionLog, setActionLog] = useState([]);
  const [agentLogs, setAgentLogs] = useState(null);
  const [logsLoading, setLogsLoading] = useState(false);
  const [showLogs, setShowLogs] = useState(false);
  
  // Auto-polling state - persisted to localStorage
  const [autoPolling, setAutoPolling] = useState(() => {
    const stored = localStorage.getItem(AGENT_POLLING_KEY);
    return stored === null ? true : stored === 'true';
  });
  
  const intervalRef = useRef(null);

  const fetchStatus = useCallback(async () => {
    if (checking) return;
    
    setChecking(true);
    try {
      const res = await apiGet("/api/v1/agent/status");
      if (!res.ok) {
        const errorData = await res.json().catch(() => ({ error: `HTTP ${res.status}` }));
        throw new Error(errorData.error || `Status check failed: ${res.status}`);
      }
      const data = await res.json();
      console.log("[AgentPanel] Status response:", data);
      setStatus(data);
    } catch (e) {
      console.error("[AgentPanel] Error fetching status:", e);
      setStatus({ status: "error", error: e.message });
    } finally {
      setLoading(false);
      setChecking(false);
    }
  }, [checking]);

  // Toggle auto-polling and persist to localStorage
  const toggleAutoPolling = useCallback(() => {
    setAutoPolling(prev => {
      const newValue = !prev;
      localStorage.setItem(AGENT_POLLING_KEY, String(newValue));
      return newValue;
    });
  }, []);

  // Manual refresh
  const manualRefresh = useCallback(() => {
    fetchStatus();
  }, [fetchStatus]);

  // Set up polling interval
  useEffect(() => {
    // Always do initial fetch
    fetchStatus();
    
    // Clean up existing interval
    if (intervalRef.current) {
      clearInterval(intervalRef.current);
      intervalRef.current = null;
    }
    
    // Set up new interval only if auto-polling is enabled
    if (autoPolling) {
      intervalRef.current = setInterval(fetchStatus, 5000);
    }

    return () => {
      if (intervalRef.current) {
        clearInterval(intervalRef.current);
        intervalRef.current = null;
      }
    };
  }, [autoPolling, fetchStatus]);

  const executeAction = async (actionId, params = {}, successMsg) => {
    setActionLoading(actionId);
    setMessage(null);

    try {
      const res = await apiPost("/api/v1/agent/action", {
        action: actionId,
        parameters: params,
        force: true,
      });
      
      if (!res.ok) {
        const errorData = await res.json().catch(() => ({ error: `HTTP ${res.status}: ${res.statusText}` }));
        throw new Error(errorData.error || `Request failed with status ${res.status}`);
      }
      
      const data = await res.json();
      
      // Log the full response for debugging
      console.log(`[AgentPanel] Action ${actionId} response:`, data);

      const logEntry = {
        time: new Date().toLocaleTimeString(),
        action: actionId,
        success: data.success === true,
        message: data.message || data.error || "Unknown response",
      };
      setActionLog((prev) => [logEntry, ...prev.slice(0, 19)]);

      if (data.success === true) {
        setMessage({ type: "success", text: successMsg || data.message || "Action completed" });
        // Refresh status after a short delay to see updated state
        setTimeout(() => fetchStatus(), 1000);
      } else if (data.requires_approval) {
        setMessage({ type: "warning", text: `Action requires approval: ${data.message}` });
      } else {
        const errorMsg = data.error || data.message || "Action failed";
        setMessage({ type: "error", text: errorMsg });
        console.error(`[AgentPanel] Action ${actionId} failed:`, errorMsg, data);
      }
    } catch (e) {
      const errorMsg = e.message || "Failed to execute action";
      setMessage({ type: "error", text: errorMsg });
      setActionLog((prev) => [
        { time: new Date().toLocaleTimeString(), action: actionId, success: false, message: errorMsg },
        ...prev.slice(0, 19),
      ]);
      console.error(`[AgentPanel] Error executing action ${actionId}:`, e);
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

  const fetchLogs = async () => {
    setLogsLoading(true);
    try {
      const res = await apiGet("/api/v1/agent/logs");
      if (!res.ok) {
        const errorData = await res.json().catch(() => ({ error: `HTTP ${res.status}` }));
        throw new Error(errorData.error || `Failed to fetch logs: ${res.status}`);
      }
      const data = await res.json();
      setAgentLogs(data);
      setShowLogs(true);
    } catch (e) {
      setAgentLogs({ error: e.message });
      setShowLogs(true);
      console.error("[AgentPanel] Error fetching logs:", e);
    } finally {
      setLogsLoading(false);
    }
  };

  const getResourceLevel = (percentage) => {
    if (percentage < 50) return "low";
    if (percentage < 80) return "medium";
    return "high";
  };

  // Polling controls component
  const PollingControls = () => (
    <div className="agent-polling-controls">
      <button
        className={`agent-polling-btn ${autoPolling ? 'active' : 'paused'}`}
        onClick={toggleAutoPolling}
        title={autoPolling ? 'Auto-polling ON (click to pause)' : 'Auto-polling OFF (click to enable)'}
      >
        {autoPolling ? '⟳' : '⏸'}
      </button>
      {(!autoPolling || status?.status === 'error') && (
        <button
          className="agent-polling-btn refresh"
          onClick={manualRefresh}
          disabled={checking}
          title="Check agent status now"
        >
          {checking ? '...' : '↻'}
        </button>
      )}
      {checking && <span className="agent-checking-indicator">●</span>}
    </div>
  );

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
          <div className="agent-header-controls">
            <PollingControls />
            <div className="agent-status-badge disabled">
              <span className="agent-status-dot disabled"></span>
              Disabled
            </div>
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
        <div className="agent-header-controls">
          <PollingControls />
          <div className={`agent-status-badge ${isOnline ? "online" : "offline"}`}>
            <span className={`agent-status-dot ${isOnline ? "online" : "offline"}`}></span>
            {isOnline ? "Online" : "Offline"}
          </div>
        </div>
      </div>

      {message && (
        <div className={`agent-message ${message.type}`}>
          {message.text}
        </div>
      )}

      <div className="agent-content">
        {!isOnline ? (
          <div className="agent-offline-content">
            <div className="agent-message error">
              <div style={{ marginBottom: "8px", fontWeight: "bold" }}>Cannot connect to agent</div>
              <div style={{ fontSize: "0.9em" }}>{status?.error || "Unknown error"}</div>
            </div>
            
            <div className="agent-offline-notice">
              <div className="agent-polling-status">
                {autoPolling ? (
                  <>
                    <span className="polling-indicator active">●</span>
                    <span>Auto-polling is ON - checking every 5 seconds</span>
                    <button className="agent-btn small" onClick={toggleAutoPolling}>
                      Pause Polling
                    </button>
                  </>
                ) : (
                  <>
                    <span className="polling-indicator paused">●</span>
                    <span>Auto-polling is OFF</span>
                    <button className="agent-btn small" onClick={toggleAutoPolling}>
                      Enable Polling
                    </button>
                    <button className="agent-btn small" onClick={manualRefresh} disabled={checking}>
                      {checking ? 'Checking...' : 'Check Now'}
                    </button>
                  </>
                )}
              </div>
            </div>
            
            <div style={{ fontSize: "0.85em", marginTop: "12px", opacity: 0.8 }}>
              Check that:
              <ul style={{ marginTop: "4px", paddingLeft: "20px" }}>
                <li>The agent URL is correct in Settings</li>
                <li>The agent server is running on the 4090 rig</li>
                <li>The API key matches between ARES and the agent</li>
                <li>Network connectivity is working (firewall, VPN, etc.)</li>
              </ul>
            </div>
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

            {/* Agent Logs */}
            <div className="agent-section">
              <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "12px" }}>
                <h3>Agent Logs</h3>
                <button
                  className="agent-btn"
                  onClick={fetchLogs}
                  disabled={logsLoading}
                >
                  {logsLoading ? "Loading..." : showLogs ? "Refresh Logs" : "View Logs"}
                </button>
              </div>
              {showLogs && agentLogs && (
                <div className="agent-logs-container">
                  {agentLogs.error ? (
                    <div style={{ color: "#ff6b6b" }}>Error: {agentLogs.error}</div>
                  ) : agentLogs.logs ? (
                    Array.isArray(agentLogs.logs) ? (
                      agentLogs.logs.map((log, idx) => (
                        <div key={idx} style={{ marginBottom: "4px", whiteSpace: "pre-wrap", wordBreak: "break-word" }}>
                          {typeof log === "string" ? log : JSON.stringify(log, null, 2)}
                        </div>
                      ))
                    ) : (
                      <div style={{ whiteSpace: "pre-wrap", wordBreak: "break-word" }}>{JSON.stringify(agentLogs.logs, null, 2)}</div>
                    )
                  ) : agentLogs.content ? (
                    <div style={{ whiteSpace: "pre-wrap", wordBreak: "break-word" }}>{agentLogs.content}</div>
                  ) : (
                    <div style={{ whiteSpace: "pre-wrap", wordBreak: "break-word" }}>{JSON.stringify(agentLogs, null, 2)}</div>
                  )}
                </div>
              )}
            </div>
          </>
        )}
      </div>
    </div>
  );
}

export default AgentPanel;
