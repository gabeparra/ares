import React from 'react'
import './LatencyDisplay.css'

function LatencyDisplay({ latency, isConnected }) {
  if (!isConnected || latency === null) return null
  
  return (
    <span className="connection-latency-display">
      {latency}ms
    </span>
  )
}

export default LatencyDisplay

