import React, { useState, useEffect, useRef } from 'react'
import { getAuthToken } from '../../services/auth'

function DiscordStatus() {
  const [status, setStatus] = useState({
    configured: false,
    running: false,
    error: null,
  })
  const [loading, setLoading] = useState(true)
  const [busy, setBusy] = useState(false)
  const statusRef = useRef({ configured: false, running: false, error: null })  // Keep a ref to track previous status

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
        // This prevents flickering when status is temporarily inconsistent
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
        setStatus(prev => ({ ...prev, error: data.error || 'Failed to start bot' }))
      }
    } catch (err) {
      console.error('Failed to start Discord bot:', err)
      setStatus(prev => ({ ...prev, error: err.message }))
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
        setStatus(prev => ({ ...prev, error: data.error || 'Failed to stop bot' }))
      }
    } catch (err) {
      console.error('Failed to stop Discord bot:', err)
      setStatus(prev => ({ ...prev, error: err.message }))
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

  let label = 'Discord Bot: Unknown'
  let statusColor = 'text-gray-400'
  let statusBg = 'bg-gray-500'
  
  if (!status.configured) {
    label = status.error ? `Discord Bot: ${status.error}` : 'Discord Bot: Not configured'
    statusColor = 'text-red-400'
    statusBg = 'bg-red-500'
  } else if (status.running) {
    label = 'Discord Bot: Running'
    statusColor = 'text-green-400'
    statusBg = 'bg-green-400'
  } else {
    label = 'Discord Bot: Stopped'
    statusColor = 'text-yellow-400'
    statusBg = 'bg-yellow-500'
  }

  return (
    <div className="flex flex-col gap-3 p-4 bg-white-opacity-3 border border-white-opacity-8 rounded-xl">
      <div className="flex items-center gap-8px font-medium">
        <span className={`w-8px h-8px rounded-full transition-all duration-300 ${
          isEnabled
            ? 'bg-green-400 shadow-[0_0_16px_rgba(34,197,94,0.6)] animate-pulse-2'
            : status.configured
            ? 'bg-yellow-500 shadow-[0_0_16px_rgba(234,179,8,0.6)]'
            : 'bg-red-500 shadow-[0_0_16px_rgba(239,68,68,0.6)]'
        }`}></span>
        <span className={`font-bold tracking-wide whitespace-nowrap transition-colors duration-300 ${statusColor}`}>
          {label}
        </span>
      </div>

      <div className="flex items-center gap-2">
        {canStop ? (
          <button
            type="button"
            className="px-4 py-2 rounded-lg cursor-pointer font-bold border border-red-500/40 bg-red-500/10 text-white text-0.85em transition-all duration-300 hover:border-red-500/60 hover:bg-red-500/20 hover:scale-105 active:scale-95 disabled:opacity-50 disabled:cursor-not-allowed"
            onClick={stop}
            disabled={busy}
            title="Stop Discord bot"
          >
            {busy ? 'Stopping...' : 'Stop Bot'}
          </button>
        ) : (
          <button
            type="button"
            className="px-4 py-2 rounded-lg cursor-pointer font-bold border border-green-400/40 bg-green-400/10 text-white text-0.85em transition-all duration-300 hover:border-green-400/60 hover:bg-green-400/20 hover:scale-105 active:scale-95 disabled:opacity-50 disabled:cursor-not-allowed"
            onClick={start}
            disabled={busy || !canStart}
            title={status.configured ? 'Start Discord bot' : 'DISCORD_BOT_TOKEN not configured'}
          >
            {busy ? 'Starting...' : 'Start Bot'}
          </button>
        )}
        <button
          type="button"
          className="px-4 py-2 rounded-lg cursor-pointer font-bold border border-white-opacity-20 bg-white-opacity-5 text-white text-0.85em transition-all duration-300 hover:border-white-opacity-30 hover:bg-white-opacity-10 hover:scale-105 active:scale-95 disabled:opacity-50 disabled:cursor-not-allowed"
          onClick={checkStatus}
          disabled={busy || loading}
          title="Refresh status"
        >
          🔄 Refresh
        </button>
      </div>

      {status.error && !status.running && (
        <div className="w-full text-red-300 text-0.85em leading-tight whitespace-nowrap overflow-hidden text-ellipsis" title={status.error}>
          {status.error}
        </div>
      )}

      {!status.configured && (
        <div className="text-white-opacity-60 text-0.8em">
          <p>Configure DISCORD_BOT_TOKEN in .env to enable the Discord bot.</p>
          <p className="mt-1">The bot will respond to mentions and DMs in Discord.</p>
        </div>
      )}

      {status.configured && status.running && (
        <div className="text-green-300 text-0.8em">
          <p>✓ Bot is running and ready to respond to Discord messages.</p>
        </div>
      )}

      {status.configured && !status.running && (
        <div className="text-yellow-300 text-0.8em">
          <p>⚠ Bot is configured but not running. Click "Start Bot" to activate it.</p>
        </div>
      )}
    </div>
  )
}

export default DiscordStatus

