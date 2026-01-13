import React, { useState, useCallback } from "react";
import { useAgentStatus, useAgentAction, useAgentLogs, getAutoPolling, setAutoPolling } from "../../hooks/useAgentStatus";
import { useQueryClient } from "@tanstack/react-query";
import { apiGet } from "../../services/api";

function AgentPanel() {
  const [autoPolling, setAutoPollingState] = useState(getAutoPolling);
  const [message, setMessage] = useState(null);
  const [vramMode, setVramMode] = useState("low");
  const [actionLog, setActionLog] = useState([]);
  const [showLogs, setShowLogs] = useState(false);
  
  const queryClient = useQueryClient();
  
  // Use React Query hooks
  const { data: status, isLoading: loading, isFetching: checking, refetch: manualRefresh, error: statusError } = useAgentStatus(autoPolling);
  const agentAction = useAgentAction();
  const { data: agentLogs, isLoading: logsLoading, error: logsError } = useAgentLogs();
  
  // Handle status error state
  const statusData = status || (statusError ? { status: "error", error: statusError.message } : null);

  // Toggle auto-polling and persist to localStorage
  const toggleAutoPolling = useCallback(() => {
    const newValue = !autoPolling;
    setAutoPolling(newValue);
    setAutoPollingState(newValue);
    // Refetch with new polling setting
    queryClient.invalidateQueries({ queryKey: ['agent', 'status'] });
  }, [autoPolling, queryClient]);

  const executeAction = async (actionId, params = {}, successMsg) => {
    setMessage(null);

    try {
      const data = await agentAction.mutateAsync({
        action: actionId,
        parameters: params,
        force: true,
      });
      
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

  const handleFetchLogs = async () => {
    try {
      setShowLogs(true);
      // Use fetchQuery to force fetch even when enabled: false
      // This ensures the query is executed and data is available
      const logsData = await queryClient.fetchQuery({
        queryKey: ['agent', 'logs'],
        queryFn: async () => {
          const res = await apiGet("/api/v1/agent/logs");
          if (!res.ok) {
            const errorData = await res.json().catch(() => ({ error: `HTTP ${res.status}` }));
            return { error: errorData.error || `Failed to fetch logs: ${res.status}` };
          }
          const data = await res.json();
          return data;
        },
        staleTime: 0, // Always fetch fresh data
      });
      console.log("[AgentPanel] Logs fetched:", logsData);
    } catch (e) {
      console.error("[AgentPanel] Error fetching logs:", e);
      setShowLogs(true);
      // Set error in query cache so UI can display it
      queryClient.setQueryData(['agent', 'logs'], { 
        error: e.message || "Failed to fetch logs" 
      });
    }
  };

  const getResourceLevel = (percentage) => {
    if (percentage < 50) return "low";
    if (percentage < 80) return "medium";
    return "high";
  };

  // Polling controls component
  const PollingControls = () => (
    <div className="flex items-center gap-2">
      <button
        className={`bg-white-opacity-6 border border-white-opacity-12 rounded-lg px-3 py-2 text-white-opacity-80 cursor-pointer text-1em transition-all duration-200 flex items-center justify-center min-w-[36px] h-9 hover:bg-white-opacity-10 hover:border-white-opacity-20 disabled:opacity-50 disabled:cursor-not-allowed ${
          autoPolling 
            ? 'bg-[rgba(34,197,94,0.15)] border-[rgba(34,197,94,0.3)] text-[#4ade80]' 
            : 'bg-[rgba(156,163,175,0.15)] border-[rgba(156,163,175,0.3)] text-[#9ca3af]'
        }`}
        onClick={toggleAutoPolling}
        title={autoPolling ? 'Auto-polling ON (click to pause)' : 'Auto-polling OFF (click to enable)'}
      >
        {autoPolling ? '⟳' : '⏸'}
      </button>
      {(!autoPolling || status?.status === 'error') && (
        <button
          className="bg-[rgba(59,130,246,0.15)] border border-[rgba(59,130,246,0.3)] rounded-lg px-3 py-2 text-[#60a5fa] cursor-pointer text-1em transition-all duration-200 flex items-center justify-center min-w-[36px] h-9 hover:bg-[rgba(59,130,246,0.2)] hover:border-[rgba(59,130,246,0.4)] disabled:opacity-50 disabled:cursor-not-allowed"
          onClick={manualRefresh}
          disabled={checking}
          title="Check agent status now"
        >
          {checking ? '...' : '↻'}
        </button>
      )}
      {checking && <span className="text-[#60a5fa] text-0.8em animate-pulse">●</span>}
    </div>
  );

  if (loading) {
    return (
      <div className="panel p-5">
        <div className="flex items-center justify-center py-10 text-white-opacity-70 text-1em">Loading agent status...</div>
      </div>
    );
  }

  if (statusData?.status === "disabled") {
    return (
      <div className="panel p-5">
        <div className="flex justify-between items-center mb-5 flex-wrap gap-3">
          <h2 className="m-0 text-1.3em font-600 bg-gradient-to-br from-white to-red-accent bg-clip-text text-transparent">Agent Control</h2>
          <div className="flex items-center gap-3 flex-wrap">
            <PollingControls />
            <div className="flex items-center gap-2 px-4 py-2 bg-[rgba(156,163,175,0.15)] rounded-[20px] text-0.85em font-500 text-[#9ca3af]">
              <span className="w-2 h-2 rounded-full bg-[#9ca3af] inline-block"></span>
              Disabled
            </div>
          </div>
        </div>
        <div className="flex flex-col items-center justify-center py-10 text-center">
          <div className="text-white-opacity-70 mb-3 leading-relaxed">
            The ARES Agent is not configured or disabled.
          </div>
          <div className="text-0.9em text-white-opacity-70" style={{ opacity: 0.7 }}>
            Configure the agent URL and API key in Settings to enable remote control of your 4090 rig.
          </div>
        </div>
      </div>
    );
  }

  const isOnline = statusData?.status === "online";
  const resources = statusData?.resources || {};
  const services = statusData?.services || {};

  return (
    <div className="panel p-5">
      <div className="flex justify-between items-center mb-5 flex-wrap gap-3">
        <h2 className="m-0 text-1.3em font-600 bg-gradient-to-br from-white to-red-accent bg-clip-text text-transparent">Agent Control</h2>
        <div className="flex items-center gap-3 flex-wrap">
          <PollingControls />
          <div className={`flex items-center gap-2 px-4 py-2 rounded-[20px] text-0.85em font-500 ${
            isOnline 
              ? 'bg-[rgba(34,197,94,0.15)] text-[#4ade80]' 
              : 'bg-[rgba(239,68,68,0.15)] text-[#f87171]'
          }`}>
            <span className={`w-2 h-2 rounded-full inline-block ${
              isOnline 
                ? 'bg-[#4ade80] shadow-[0_0_8px_rgba(74,222,128,0.5)]' 
                : 'bg-[#f87171] shadow-[0_0_8px_rgba(248,113,113,0.5)]'
            }`}></span>
            {isOnline ? "Online" : "Offline"}
          </div>
        </div>
      </div>

      {message && (
        <div className={`p-3 px-4 rounded-lg mb-4 text-0.9em leading-[1.5] ${
          message.type === 'success' 
            ? 'bg-[rgba(34,197,94,0.15)] text-[#4ade80] border border-[rgba(34,197,94,0.3)]' 
            : message.type === 'error'
            ? 'bg-[rgba(239,68,68,0.15)] text-[#f87171] border border-[rgba(239,68,68,0.3)]'
            : 'bg-[rgba(245,158,11,0.15)] text-[#fbbf24] border border-[rgba(245,158,11,0.3)]'
        }`}>
          {message.text}
        </div>
      )}

      <div className="flex flex-col flex-1 min-h-0 overflow-y-auto gap-5">
        {!isOnline ? (
          <div className="flex flex-col gap-4">
            <div className="p-3 px-4 rounded-lg mb-4 text-0.9em leading-[1.5] bg-[rgba(239,68,68,0.15)] text-[#f87171] border border-[rgba(239,68,68,0.3)]">
              <div style={{ marginBottom: "8px", fontWeight: "bold" }}>Cannot connect to agent</div>
              <div style={{ fontSize: "0.9em" }}>{statusData?.error || "Unknown error"}</div>
            </div>
            
            <div className="p-4 bg-white-opacity-3 border border-white-opacity-8 rounded-xl">
              <div className="flex items-center gap-3 flex-wrap">
                {autoPolling ? (
                  <>
                    <span className="text-0.8em text-[#4ade80] animate-pulse">●</span>
                    <span>Auto-polling is ON - checking every 5 seconds</span>
                    <button className="px-3 py-1.5 bg-gradient-to-br from-red-bg-5 to-red-bg-6 border border-red-border-3 rounded-lg text-white text-0.85em font-500 cursor-pointer transition-all duration-200 hover:from-red-bg-6 hover:to-red-bg-5 hover:-translate-y-0.5 hover:shadow-[0_4px_12px_rgba(255,0,0,0.2)]" onClick={toggleAutoPolling}>
                      Pause Polling
                    </button>
                  </>
                ) : (
                  <>
                    <span className="text-0.8em text-[#9ca3af]">●</span>
                    <span>Auto-polling is OFF</span>
                    <button className="px-3 py-1.5 bg-gradient-to-br from-red-bg-5 to-red-bg-6 border border-red-border-3 rounded-lg text-white text-0.85em font-500 cursor-pointer transition-all duration-200 hover:from-red-bg-6 hover:to-red-bg-5 hover:-translate-y-0.5 hover:shadow-[0_4px_12px_rgba(255,0,0,0.2)]" onClick={toggleAutoPolling}>
                      Enable Polling
                    </button>
                    <button className="px-3 py-1.5 bg-gradient-to-br from-red-bg-5 to-red-bg-6 border border-red-border-3 rounded-lg text-white text-0.85em font-500 cursor-pointer transition-all duration-200 hover:from-red-bg-6 hover:to-red-bg-5 hover:-translate-y-0.5 hover:shadow-[0_4px_12px_rgba(255,0,0,0.2)] disabled:opacity-50 disabled:cursor-not-allowed disabled:transform-none" onClick={manualRefresh} disabled={checking}>
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
            <div className="flex flex-col gap-3">
              <h3 className="m-0 text-1.1em font-600 text-white-opacity-90">System Resources</h3>
              <div className="flex flex-col gap-4">
                {resources.gpu_memory_used !== undefined && (
                  <div className="flex flex-col gap-2">
                    <div className="flex justify-between items-center text-0.9em text-white-opacity-80">
                      <span>GPU Memory</span>
                      <span className="font-500 text-white-opacity-90">
                        {resources.gpu_memory_used} / {resources.gpu_memory_total} MB
                      </span>
                    </div>
                    <div className="w-full h-2 bg-white-opacity-10 rounded overflow-hidden">
                      <div
                        className={`h-full rounded transition-[width] duration-300 ${
                          getResourceLevel(resources.gpu_memory_percent || 0) === 'low' 
                            ? 'bg-gradient-to-r from-[#4ade80] to-[#22c55e]'
                            : getResourceLevel(resources.gpu_memory_percent || 0) === 'medium'
                            ? 'bg-gradient-to-r from-[#fbbf24] to-[#f59e0b]'
                            : 'bg-gradient-to-r from-[#f87171] to-[#ef4444]'
                        }`}
                        style={{ width: `${resources.gpu_memory_percent || 0}%` }}
                      ></div>
                    </div>
                  </div>
                )}
                {resources.cpu_percent !== undefined && (
                  <div className="flex flex-col gap-2">
                    <div className="flex justify-between items-center text-0.9em text-white-opacity-80">
                      <span>CPU Usage</span>
                      <span className="font-500 text-white-opacity-90">{resources.cpu_percent}%</span>
                    </div>
                    <div className="w-full h-2 bg-white-opacity-10 rounded overflow-hidden">
                      <div
                        className={`h-full rounded transition-[width] duration-300 ${
                          getResourceLevel(resources.cpu_percent) === 'low' 
                            ? 'bg-gradient-to-r from-[#4ade80] to-[#22c55e]'
                            : getResourceLevel(resources.cpu_percent) === 'medium'
                            ? 'bg-gradient-to-r from-[#fbbf24] to-[#f59e0b]'
                            : 'bg-gradient-to-r from-[#f87171] to-[#ef4444]'
                        }`}
                        style={{ width: `${resources.cpu_percent}%` }}
                      ></div>
                    </div>
                  </div>
                )}
                {resources.ram_percent !== undefined && (
                  <div className="flex flex-col gap-2">
                    <div className="flex justify-between items-center text-0.9em text-white-opacity-80">
                      <span>RAM Usage</span>
                      <span className="font-500 text-white-opacity-90">{resources.ram_percent}%</span>
                    </div>
                    <div className="w-full h-2 bg-white-opacity-10 rounded overflow-hidden">
                      <div
                        className={`h-full rounded transition-[width] duration-300 ${
                          getResourceLevel(resources.ram_percent) === 'low' 
                            ? 'bg-gradient-to-r from-[#4ade80] to-[#22c55e]'
                            : getResourceLevel(resources.ram_percent) === 'medium'
                            ? 'bg-gradient-to-r from-[#fbbf24] to-[#f59e0b]'
                            : 'bg-gradient-to-r from-[#f87171] to-[#ef4444]'
                        }`}
                        style={{ width: `${resources.ram_percent}%` }}
                      ></div>
                    </div>
                  </div>
                )}
              </div>
              <div style={{ marginTop: "12px" }}>
                <button
                  className="px-4.5 py-2.5 bg-gradient-to-br from-red-bg-5 to-red-bg-6 border border-red-border-3 rounded-lg text-white text-0.9em font-500 cursor-pointer transition-all duration-200 hover:from-red-bg-6 hover:to-red-bg-5 hover:-translate-y-0.5 hover:shadow-[0_4px_12px_rgba(255,0,0,0.2)] disabled:opacity-50 disabled:cursor-not-allowed disabled:transform-none"
                  onClick={handleRefreshResources}
                  disabled={agentAction.isPending}
                >
                  Refresh
                </button>
              </div>
            </div>

            {/* Services */}
            <div className="flex flex-col gap-3">
              <h3 className="m-0 text-1.1em font-600 text-white-opacity-90">Services</h3>
              <div className="flex flex-col gap-3">
                {/* Stable Diffusion */}
                <div className="bg-white-opacity-3 border border-white-opacity-8 rounded-xl p-4 transition-all duration-200 hover:bg-white-opacity-5 hover:border-white-opacity-12">
                  <div className="flex justify-between items-center mb-3">
                    <span className="font-500 text-white-opacity-90 text-1em">Stable Diffusion</span>
                    <span className={`px-3 py-1 rounded text-0.85em font-500 ${
                      services.sd?.running 
                        ? "bg-[rgba(34,197,94,0.15)] text-[#4ade80]" 
                        : "bg-[rgba(239,68,68,0.15)] text-[#f87171]"
                    }`}>
                      {services.sd?.running ? "Running" : "Stopped"}
                    </span>
                  </div>
                  <div className="flex items-center gap-3 flex-wrap">
                    {!services.sd?.running ? (
                      <>
                        <div className="flex items-center gap-2">
                          <label className="text-0.9em text-white-opacity-70">VRAM:</label>
                          <select value={vramMode} onChange={(e) => setVramMode(e.target.value)} className="px-3 py-2 bg-white-opacity-6 border border-white-opacity-12 rounded-lg text-white text-0.9em cursor-pointer outline-none transition-all duration-200 focus:border-red-border-4">
                            <option value="low" className="bg-[#1a1a1f]">Low (~4GB)</option>
                            <option value="medium" className="bg-[#1a1a1f]">Medium (~8GB)</option>
                            <option value="full" className="bg-[#1a1a1f]">Full (~12GB)</option>
                          </select>
                        </div>
                        <button
                          className="px-4.5 py-2.5 bg-gradient-to-br from-green-bg-2 to-green-bg-1 border border-green-border-1 rounded-lg text-white text-0.9em font-500 cursor-pointer transition-all duration-200 hover:from-green-bg-1 hover:to-green-bg-2 hover:-translate-y-0.5 hover:shadow-[0_4px_12px_rgba(34,197,94,0.2)] disabled:opacity-50 disabled:cursor-not-allowed disabled:transform-none"
                          onClick={handleStartSD}
                          disabled={agentAction.isPending}
                        >
                          {agentAction.isPending ? "Starting..." : "Start"}
                        </button>
                      </>
                    ) : (
                      <button
                        className="px-4.5 py-2.5 bg-gradient-to-br from-[rgba(239,68,68,0.2)] to-[rgba(239,68,68,0.3)] border border-[rgba(239,68,68,0.3)] rounded-lg text-white text-0.9em font-500 cursor-pointer transition-all duration-200 hover:from-[rgba(239,68,68,0.3)] hover:to-[rgba(239,68,68,0.4)] hover:-translate-y-0.5 hover:shadow-[0_4px_12px_rgba(239,68,68,0.2)] disabled:opacity-50 disabled:cursor-not-allowed disabled:transform-none"
                        onClick={handleStopSD}
                        disabled={agentAction.isPending}
                      >
                        {agentAction.isPending ? "Stopping..." : "Stop"}
                      </button>
                    )}
                  </div>
                </div>

                {/* Ollama */}
                <div className="bg-white-opacity-3 border border-white-opacity-8 rounded-xl p-4 transition-all duration-200 hover:bg-white-opacity-5 hover:border-white-opacity-12">
                  <div className="flex justify-between items-center mb-3">
                    <span className="font-500 text-white-opacity-90 text-1em">Ollama</span>
                    <span className={`px-3 py-1 rounded text-0.85em font-500 ${
                      services.ollama?.running 
                        ? "bg-[rgba(34,197,94,0.15)] text-[#4ade80]" 
                        : "bg-[rgba(239,68,68,0.15)] text-[#f87171]"
                    }`}>
                      {services.ollama?.running ? "Running" : "Stopped"}
                    </span>
                  </div>
                  <div className="flex items-center gap-3 flex-wrap">
                    {!services.ollama?.running ? (
                      <button
                        className="px-4.5 py-2.5 bg-gradient-to-br from-green-bg-2 to-green-bg-1 border border-green-border-1 rounded-lg text-white text-0.9em font-500 cursor-pointer transition-all duration-200 hover:from-green-bg-1 hover:to-green-bg-2 hover:-translate-y-0.5 hover:shadow-[0_4px_12px_rgba(34,197,94,0.2)] disabled:opacity-50 disabled:cursor-not-allowed disabled:transform-none"
                        onClick={() => executeAction("start_ollama", {}, "Starting Ollama")}
                        disabled={agentAction.isPending}
                      >
                        {agentAction.isPending ? "Starting..." : "Start"}
                      </button>
                    ) : (
                      <button
                        className="px-4.5 py-2.5 bg-gradient-to-br from-[rgba(239,68,68,0.2)] to-[rgba(239,68,68,0.3)] border border-[rgba(239,68,68,0.3)] rounded-lg text-white text-0.9em font-500 cursor-pointer transition-all duration-200 hover:from-[rgba(239,68,68,0.3)] hover:to-[rgba(239,68,68,0.4)] hover:-translate-y-0.5 hover:shadow-[0_4px_12px_rgba(239,68,68,0.2)] disabled:opacity-50 disabled:cursor-not-allowed disabled:transform-none"
                        onClick={() => executeAction("stop_ollama", {}, "Stopping Ollama")}
                        disabled={agentAction.isPending}
                      >
                        {agentAction.isPending ? "Stopping..." : "Stop"}
                      </button>
                    )}
                  </div>
                </div>
              </div>
            </div>

            {/* Action Log */}
            {actionLog.length > 0 && (
              <div className="flex flex-col gap-3">
                <h3 className="m-0 text-1.1em font-600 text-white-opacity-90">Recent Actions</h3>
                <div className="flex flex-col gap-2 max-h-[300px] overflow-y-auto bg-white-opacity-2 border border-white-opacity-8 rounded-lg p-3">
                  {actionLog.map((entry, idx) => (
                    <div key={idx} className="flex gap-3 items-start px-2 py-2 bg-white-opacity-2 rounded text-0.85em leading-[1.5]">
                      <span className="text-white-opacity-50 font-mono text-0.8em min-w-[80px]">{entry.time}</span>
                      <span className="text-white-opacity-70 font-500 min-w-[120px]">{entry.action}</span>
                      <span className={`flex-1 ${entry.success ? "text-[#4ade80]" : "text-[#f87171]"}`}>
                        {entry.success ? "OK" : "FAIL"}: {entry.message}
                      </span>
                    </div>
                  ))}
                </div>
              </div>
            )}

            {/* Agent Logs */}
            <div className="flex flex-col gap-3">
              <div className="flex justify-between items-center mb-3">
                <h3 className="m-0 text-1.1em font-600 text-white-opacity-90">Agent Logs</h3>
                <button
                  className="px-4.5 py-2.5 bg-gradient-to-br from-red-bg-5 to-red-bg-6 border border-red-border-3 rounded-lg text-white text-0.9em font-500 cursor-pointer transition-all duration-200 hover:from-red-bg-6 hover:to-red-bg-5 hover:-translate-y-0.5 hover:shadow-[0_4px_12px_rgba(255,0,0,0.2)] disabled:opacity-50 disabled:cursor-not-allowed disabled:transform-none"
                  onClick={handleFetchLogs}
                  disabled={logsLoading}
                >
                  {logsLoading ? "Loading..." : showLogs ? "Refresh Logs" : "View Logs"}
                </button>
              </div>
              {showLogs && (
                <div className="bg-white-opacity-2 border border-white-opacity-8 rounded-lg p-4 max-h-[400px] overflow-y-auto font-mono text-0.85em leading-relaxed text-white-opacity-80">
                  {logsLoading ? (
                    <div style={{ color: "rgba(255, 255, 255, 0.7)", textAlign: "center", padding: "20px" }}>
                      Loading logs...
                    </div>
                  ) : logsError ? (
                    <div style={{ color: "#ff6b6b" }}>Error: {logsError.message || String(logsError)}</div>
                  ) : agentLogs?.error ? (
                    <div style={{ color: "#ff6b6b" }}>Error: {agentLogs.error}</div>
                  ) : agentLogs?.logs ? (
                    Array.isArray(agentLogs.logs) ? (
                      agentLogs.logs.length > 0 ? (
                        agentLogs.logs.map((log, idx) => (
                          <div key={idx} style={{ marginBottom: "4px", whiteSpace: "pre-wrap", wordBreak: "break-word" }}>
                            {typeof log === "string" ? log : JSON.stringify(log, null, 2)}
                          </div>
                        ))
                      ) : (
                        <div style={{ color: "rgba(255, 255, 255, 0.5)", textAlign: "center", padding: "20px" }}>
                          No logs available
                        </div>
                      )
                    ) : (
                      <div style={{ whiteSpace: "pre-wrap", wordBreak: "break-word" }}>{JSON.stringify(agentLogs.logs, null, 2)}</div>
                    )
                  ) : agentLogs?.content ? (
                    <div style={{ whiteSpace: "pre-wrap", wordBreak: "break-word" }}>{agentLogs.content}</div>
                  ) : agentLogs ? (
                    <div style={{ whiteSpace: "pre-wrap", wordBreak: "break-word" }}>{JSON.stringify(agentLogs, null, 2)}</div>
                  ) : (
                    <div style={{ color: "rgba(255, 255, 255, 0.5)", textAlign: "center", padding: "20px" }}>
                      Click "View Logs" to fetch agent logs
                    </div>
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
