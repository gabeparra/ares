import { useState, useEffect } from 'react'

function useConnectionStatus() {
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
    const interval = setInterval(checkConnection, 5000)

    return () => clearInterval(interval)
  }, [])

  return { isConnected, latency }
}

export default useConnectionStatus

