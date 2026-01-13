import React from 'react'

function LatencyDisplay({ latency, isConnected }) {
  if (!isConnected || latency === null) return null

  return (
    <span className="text-white-opacity-60 text-0.75em font-mono bg-white-opacity-5 px-6px py-1px rounded-md leading-tight whitespace-nowrap flex-shrink-0 block ml-0">
      {latency}ms
    </span>
  )
}

export default LatencyDisplay

