import React from 'react'
import './StatusText.css'

function StatusText({ isConnected }) {
  return (
    <span className={`connection-status-text ${isConnected ? 'connection-status-connected' : 'connection-status-disconnected'}`}>
      {isConnected ? 'Connected' : 'Disconnected'}
    </span>
  )
}

export default StatusText

