import React from 'react'
import StatusDot from './StatusDot'
import StatusText from './StatusText'
import LatencyDisplay from './LatencyDisplay'
import useConnectionStatus from './useConnectionStatus'
import './ConnectionStatus.css'

function ConnectionStatus() {
  const { 
    isConnected, 
    latency, 
    checking,
    error,
    autoReconnect,
    toggleAutoReconnect,
    reconnect
  } = useConnectionStatus()

  return (
    <div className="connection-status">
      <div className="connection-status-indicator">
        <StatusDot isConnected={isConnected} />
        <StatusText isConnected={isConnected} />
        {checking && <span className="connection-checking">●</span>}
      </div>
      
      {isConnected && latency !== null && (
        <LatencyDisplay latency={latency} isConnected={isConnected} />
      )}
      
      {!isConnected && error && (
        <span className="connection-error" title={error}>
          {error.length > 25 ? error.substring(0, 25) + '...' : error}
        </span>
      )}
      
      <div className="connection-controls">
        <button
          className={`connection-btn auto-reconnect-btn ${autoReconnect ? 'active' : 'paused'}`}
          onClick={toggleAutoReconnect}
          title={autoReconnect ? 'Auto-reconnect ON (click to pause)' : 'Auto-reconnect OFF (click to enable)'}
        >
          {autoReconnect ? '⟳' : '⏸'}
        </button>
        
        {(!autoReconnect || !isConnected) && (
          <button
            className="connection-btn reconnect-btn"
            onClick={reconnect}
            disabled={checking}
            title="Reconnect now"
          >
            {checking ? '...' : '↻'}
          </button>
        )}
      </div>
    </div>
  )
}

export default ConnectionStatus
