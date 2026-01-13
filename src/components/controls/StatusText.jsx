import React from 'react'

function StatusText({ isConnected }) {
  return (
    <span className={`font-semibold tracking-wide leading-tight whitespace-nowrap flex-shrink-0 inline-block ${
      isConnected ? 'text-green-400/90' : 'text-red-500/90'
    }`}>
      {isConnected ? 'Connected' : 'Disconnected'}
    </span>
  )
}

export default StatusText

