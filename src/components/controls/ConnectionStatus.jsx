import React from 'react'
import StatusDot from './StatusDot'
import StatusText from './StatusText'
import LatencyDisplay from './LatencyDisplay'
import useConnectionStatus from './useConnectionStatus'
import './ConnectionStatus.css'

function ConnectionStatus() {
  const { isConnected, latency } = useConnectionStatus()

  return (
    <div className="connection-status">
      <div className="connection-status-indicator">
        <StatusDot isConnected={isConnected} />
        <StatusText isConnected={isConnected} />
      </div>
      {isConnected && latency !== null && (
        <LatencyDisplay latency={latency} isConnected={isConnected} />
      )}
    </div>
  )
}

export default ConnectionStatus
