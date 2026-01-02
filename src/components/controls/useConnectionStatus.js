import { useState, useEffect, useCallback, useRef } from 'react'

const STORAGE_KEY = 'ares_auto_reconnect'

function useConnectionStatus() {
  const [isConnected, setIsConnected] = useState(false)
  const [latency, setLatency] = useState(null)
  const [checking, setChecking] = useState(false)
  const [error, setError] = useState(null)
  // Auto-reconnect is enabled by default, stored in localStorage
  const [autoReconnect, setAutoReconnect] = useState(() => {
    const stored = localStorage.getItem(STORAGE_KEY)
    return stored === null ? true : stored === 'true'
  })
  
  const intervalRef = useRef(null)

  const checkConnection = useCallback(async () => {
    if (checking) return
    
    setChecking(true)
    const startTime = Date.now()
    
    try {
      const headers = {}
      if (window.authToken) {
        headers['Authorization'] = `Bearer ${window.authToken}`
      }
      
      // Use provider settings endpoint as a lightweight health check
      // This doesn't try to connect to Ollama
      const response = await fetch('/api/v1/settings/provider', { 
        headers,
        signal: AbortSignal.timeout(5000)
      })
      
      const endTime = Date.now()
      const responseTime = endTime - startTime
      
      // Check if the response is JSON (not an HTML error page)
      const contentType = response.headers.get('content-type')
      if (contentType && contentType.includes('text/html')) {
        throw new Error('Backend returned HTML instead of JSON - check server status')
      }
      
      if (response.ok) {
        setIsConnected(true)
        setLatency(responseTime)
        setError(null)
      } else {
        // Try to parse error response safely
        let errorMsg = `HTTP ${response.status}`
        try {
          const data = await response.json()
          errorMsg = data.error || errorMsg
        } catch {
          // If JSON parsing fails, use status text
          errorMsg = response.statusText || errorMsg
        }
        setIsConnected(false)
        setLatency(null)
        setError(errorMsg)
      }
    } catch (err) {
      setIsConnected(false)
      setLatency(null)
      
      // Provide more helpful error messages
      if (err.name === 'AbortError' || err.name === 'TimeoutError') {
        setError('Connection timeout')
      } else if (err.message.includes('Failed to fetch')) {
        setError('Cannot reach backend')
      } else {
        setError(err.message || 'Connection failed')
      }
    } finally {
      setChecking(false)
    }
  }, [checking])

  // Toggle auto-reconnect and persist to localStorage
  const toggleAutoReconnect = useCallback(() => {
    setAutoReconnect(prev => {
      const newValue = !prev
      localStorage.setItem(STORAGE_KEY, String(newValue))
      return newValue
    })
  }, [])

  // Manual reconnect function
  const reconnect = useCallback(() => {
    checkConnection()
  }, [checkConnection])

  // Set up interval when auto-reconnect is enabled
  useEffect(() => {
    // Always do initial check
    checkConnection()
    
    // Clean up existing interval
    if (intervalRef.current) {
      clearInterval(intervalRef.current)
      intervalRef.current = null
    }
    
    // Set up new interval if auto-reconnect is enabled
    // Poll every 30 seconds - provider settings don't change frequently
    if (autoReconnect) {
      intervalRef.current = setInterval(checkConnection, 30000)
    }

    return () => {
      if (intervalRef.current) {
        clearInterval(intervalRef.current)
        intervalRef.current = null
      }
    }
  }, [autoReconnect, checkConnection])

  return { 
    isConnected, 
    latency, 
    checking,
    error,
    autoReconnect,
    toggleAutoReconnect,
    reconnect
  }
}

export default useConnectionStatus
