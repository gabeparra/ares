import React from 'react'
import StatusDot from './StatusDot'
import StatusText from './StatusText'
import LatencyDisplay from './LatencyDisplay'
import useConnectionStatus from './useConnectionStatus'

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
    <div className="flex items-center gap-8px px-12px py-6px bg-white-opacity-6 border border-white-opacity-12 rounded-xl text-0.85em backdrop-blur-8px transition-all duration-300 hover:bg-white-opacity-8 hover:border-white-opacity-16 hover:shadow-glass">
      <div className="flex items-center gap-6px flex-shrink-0">
        <StatusDot isConnected={isConnected} />
        <StatusText isConnected={isConnected} />
        {checking && <span className="text-yellow-400 text-0.7em animate-pulse">●</span>}
      </div>

      {isConnected && latency !== null && (
        <LatencyDisplay latency={latency} isConnected={isConnected} />
      )}

      {!isConnected && error && (
        <span className="text-red-400 text-0.8em opacity-90 max-w-160px overflow-hidden text-ellipsis whitespace-nowrap" title={error}>
          {error.length > 25 ? error.substring(0, 25) + '...' : error}
        </span>
      )}

      <div className="flex items-center gap-6px ml-auto">
        <button
          className={`w-28px h-28px border-none rounded-lg cursor-pointer flex items-center justify-center text-1em transition-all duration-300 hover:scale-110 active:scale-95 ${
            autoReconnect
              ? 'bg-green-500/20 text-green-400 hover:bg-green-500/30 shadow-[0_0_12px_rgba(34,197,94,0.3)]'
              : 'bg-orange-500/20 text-orange-400 hover:bg-orange-500/30 shadow-[0_0_12px_rgba(249,115,22,0.3)]'
          }`}
          onClick={toggleAutoReconnect}
          title={autoReconnect ? 'Auto-reconnect ON (click to pause)' : 'Auto-reconnect OFF (click to enable)'}
        >
          {autoReconnect ? '⟳' : '⏸'}
        </button>

        {(!autoReconnect || !isConnected) && (
          <button
            className="w-28px h-28px border-none rounded-lg cursor-pointer flex items-center justify-center text-1em transition-all duration-300 bg-white-opacity-10 text-white-opacity-70 hover:bg-blue-500/25 hover:text-blue-400 hover:scale-110 active:scale-95 disabled:opacity-40 disabled:cursor-not-allowed"
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
