import React from 'react'

function StatusDot({ isConnected }) {
  return (
    <span 
      className={`w-8px h-8px min-w-8px min-h-8px flex-shrink-0 rounded-full inline-block ${
        isConnected 
          ? 'bg-green-400 shadow-[0_0_12px_rgba(0,255,136,0.6)] animate-connection-status-pulse' 
          : 'bg-red-500 shadow-[0_0_12px_rgba(255,68,68,0.6)]'
      }`}
      aria-hidden="true"
    />
  )
}

export default StatusDot

