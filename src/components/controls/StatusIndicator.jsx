import React from 'react'

function StatusIndicator({ connected }) {
  return (
    <div className={`bg-dark-surface border px-12px py-6px rounded-3xl text-0.8em flex items-center gap-8px transition-all duration-200ms whitespace-nowrap ${
      connected 
        ? 'border-green-500 text-green-500' 
        : 'border-red text-red'
    }`}>
      <span className={`inline-block w-10px h-10px rounded-full flex-shrink-0 animate-pulse-2 shadow-[0_0_8px_currentColor] ${
        connected ? 'bg-green-500' : 'bg-red'
      }`}></span>
      <span className="font-bold leading-none">{connected ? 'Connected' : 'Disconnected'}</span>
    </div>
  )
}

export default StatusIndicator

