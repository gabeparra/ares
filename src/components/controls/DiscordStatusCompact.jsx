import React, { useState, useEffect, useRef } from 'react'
import { getAuthToken } from '../../services/auth'

function DiscordStatusCompact() {
  const [status, setStatus] = useState({
    configured: false,
    running: false,
    error: null,
  })
  const [loading, setLoading] = useState(true)
  const [busy, setBusy] = useState(false)
  const statusRef = useRef({ configured: false, running: false, error: null })

  useEffect(() => {
    checkStatus()
    // Poll status every 1 minute
    const interval = setInterval(checkStatus, 60000)
    return () => clearInterval(interval)
  }, [])

  const checkStatus = async () => {
    setLoading(true)
    try {
      const headers = {}
      const token = getAuthToken()
      if (token) {
        headers['Authorization'] = `Bearer ${token}`
      }
      const response = await fetch('/api/v1/discord/bot/status', { headers })
      if (response.ok) {
        const data = await response.json()
        const newStatus = {
          configured: !!data.configured,
          running: !!data.running,
          error: data.error || null,
        }
        
        // Debounce: Only update if status actually changed
        const prevStatus = statusRef.current
        if (prevStatus.running !== newStatus.running || 
            prevStatus.configured !== newStatus.configured ||
            prevStatus.error !== newStatus.error) {
          setStatus(newStatus)
          statusRef.current = newStatus
        }
      } else {
        const data = await response.json().catch(() => ({}))
        const newStatus = {
          configured: false,
          running: false,
          error: data.error || 'Failed to check status',
        }
        setStatus(newStatus)
        statusRef.current = newStatus
      }
    } catch (err) {
      console.error('Failed to check Discord status:', err)
      const newStatus = {
        configured: false,
        running: false,
        error: err.message,
      }
      setStatus(newStatus)
      statusRef.current = newStatus
    } finally {
      setLoading(false)
    }
  }

  const start = async () => {
    setBusy(true)
    try {
      const headers = { 'Content-Type': 'application/json' }
      const token = getAuthToken()
      if (token) {
        headers['Authorization'] = `Bearer ${token}`
      }
      const res = await fetch('/api/v1/discord/bot/start', { 
        method: 'POST', 
        headers 
      })
      if (res.ok) {
        await checkStatus()
      } else {
        const data = await res.json().catch(() => ({}))
        console.error('Failed to start Discord bot:', data.error || res.status)
      }
    } catch (err) {
      console.error('Failed to start Discord bot:', err)
    } finally {
      setBusy(false)
    }
  }

  const stop = async () => {
    setBusy(true)
    try {
      const headers = { 'Content-Type': 'application/json' }
      const token = getAuthToken()
      if (token) {
        headers['Authorization'] = `Bearer ${token}`
      }
      const res = await fetch('/api/v1/discord/bot/stop', { 
        method: 'POST', 
        headers 
      })
      if (res.ok) {
        await checkStatus()
      } else {
        const data = await res.json().catch(() => ({}))
        console.error('Failed to stop Discord bot:', data.error || res.status)
      }
    } catch (err) {
      console.error('Failed to stop Discord bot:', err)
    } finally {
      setBusy(false)
    }
  }

  if (loading && !status.configured) {
    return (
      <div className="flex items-center gap-8px px-12px py-6px bg-white-opacity-6 border border-white-opacity-12 rounded-xl text-0.85em backdrop-blur-8px transition-all duration-300 flex-wrap hover:bg-white-opacity-8 hover:border-white-opacity-16 hover:shadow-glass">
        <div className="flex items-center gap-8px font-medium">
          <span className="w-8px h-8px rounded-full bg-orange-500 shadow-[0_0_16px_rgba(249,115,22,0.5)] animate-pulse-2"></span>
          <span className="text-white font-bold tracking-wide whitespace-nowrap">Discord: Checking...</span>
        </div>
      </div>
    )
  }

  const canStart = status.configured && !status.running
  const canStop = status.running

  const isEnabled = status.running
  const isDisabled = !status.configured || !status.running

  let label = 'Discord: Disabled'
  if (!status.configured) {
    label = status.error ? `Discord: ${status.error}` : 'Discord: Not configured'
  } else if (status.running) {
    label = 'Discord: Running'
  } else {
    label = 'Discord: Stopped'
  }

  return (
    <div className="flex items-center gap-8px px-12px py-6px bg-white-opacity-6 border border-white-opacity-12 rounded-xl text-0.85em backdrop-blur-8px transition-all duration-300 flex-wrap hover:bg-white-opacity-8 hover:border-white-opacity-16 hover:shadow-glass">
      <div className={`flex items-center gap-6px font-medium`}>
        <span className={`w-8px h-8px rounded-full transition-all duration-300 ${
          isEnabled
            ? 'bg-green-400 shadow-[0_0_16px_rgba(34,197,94,0.6)] animate-pulse-2'
            : status.configured
            ? 'bg-yellow-500 shadow-[0_0_16px_rgba(234,179,8,0.6)]'
            : 'bg-red-500 shadow-[0_0_16px_rgba(239,68,68,0.6)]'
        }`}></span>
        <span className={`font-bold tracking-wide whitespace-nowrap transition-colors duration-300 ${
          isEnabled ? 'text-green-400' : status.configured ? 'text-yellow-400' : 'text-red-400'
        }`}>
          {label}
        </span>
      </div>

      <div className="flex items-center">
        {canStop ? (
          <button
            type="button"
            className="px-10px py-5px rounded-lg cursor-pointer font-bold border border-red-500/40 bg-red-500/10 text-white text-0.85em transition-all duration-300 hover:border-red-500/60 hover:bg-red-500/20 hover:scale-105 active:scale-95 disabled:opacity-50 disabled:cursor-not-allowed"
            onClick={stop}
            disabled={busy}
            title="Stop Discord bot"
          >
            Stop
          </button>
        ) : (
          <button
            type="button"
            className="px-10px py-5px rounded-lg cursor-pointer font-bold border border-green-400/40 bg-green-400/10 text-white text-0.85em transition-all duration-300 hover:border-green-400/60 hover:bg-green-400/20 hover:scale-105 active:scale-95 disabled:opacity-50 disabled:cursor-not-allowed"
            onClick={start}
            disabled={busy || !canStart}
            title={status.configured ? 'Start Discord bot' : 'DISCORD_BOT_TOKEN not configured'}
          >
            Start
          </button>
        )}
      </div>

      {status.error && !status.running && (
        <div className="w-full text-red-300 text-0.85em leading-tight whitespace-nowrap overflow-hidden text-ellipsis" title={status.error}>
          {status.error}
        </div>
      )}
    </div>
  )
}

export default DiscordStatusCompact

