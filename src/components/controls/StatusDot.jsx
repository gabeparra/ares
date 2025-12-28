import React from 'react'
import './StatusDot.css'

function StatusDot({ isConnected }) {
  return (
    <span 
      className={`connection-status-dot ${isConnected ? 'connection-status-connected' : 'connection-status-disconnected'}`}
      aria-hidden="true"
    />
  )
}

export default StatusDot

