import React, { useState, useEffect } from 'react'
import './ConnectionStatus.css'

function ConnectionStatus() {
  const [isConnected, setIsConnected] = useState(false)
  const [latency, setLatency] = useState(null)

  useEffect(() => {
    const checkConnection = async () => {
      const startTime = Date.now()
      try {
        const headers = {}
        if (window.authToken) {
          headers['Authorization'] = `Bearer ${window.authToken}`
        }
        const response = await fetch('/api/v1/models', { 
          headers,
          signal: AbortSignal.timeout(3000)
        })
        const endTime = Date.now()
        const responseTime = endTime - startTime
        
        if (response.ok) {
          setIsConnected(true)
          setLatency(responseTime)
        } else {
          setIsConnected(false)
          setLatency(null)
        }
      } catch (error) {
        setIsConnected(false)
        setLatency(null)
      }
    }

    checkConnection()
    const interval = setInterval(checkConnection, 5000) // Check every 5 seconds

    return () => clearInterval(interval)
  }, [])

  return (
    <div className="connection-status">
      <div className={`status-indicator ${isConnected ? 'connected' : 'disconnected'}`}>
        <span className="status-dot"></span>
        <span className="status-text">
          {isConnected ? 'Connected' : 'Disconnected'}
        </span>
      </div>
      {isConnected && latency !== null && (
        <div className="latency-info">
          {latency}ms
        </div>
      )}
    </div>
  )
}

export default ConnectionStatus

