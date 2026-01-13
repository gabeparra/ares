import React, { useState, useEffect } from 'react'
import { getAuthToken } from '../../services/auth'

function TelegramStatus() {
  const [status, setStatus] = useState({
    token_configured: false,
    enabled: false,
    connected: false,
    error: null,
  })
  const [loading, setLoading] = useState(true)
  const [busy, setBusy] = useState(false)

  useEffect(() => {
    checkStatus()
  }, [])

  const checkStatus = async () => {
    setLoading(true)
    try {
      const headers = {}
      const token = getAuthToken()
      if (token) {
        headers['Authorization'] = `Bearer ${token}`
      }
      const response = await fetch('/api/v1/telegram/status', { headers })
      if (response.ok) {
        const data = await response.json()
        setStatus({
          token_configured: !!data.token_configured,
          enabled: !!data.enabled,
          connected: !!data.connected,
          error: data.error || null,
        })
      }
    } catch (err) {
      console.error('Failed to check Telegram status:', err)
    } finally {
      setLoading(false)
    }
  }

  const disconnect = async () => {
    setBusy(true)
    try {
      const headers = { 'Content-Type': 'application/json' }
      const token = getAuthToken()
      if (token) {
        headers['Authorization'] = `Bearer ${token}`
      }
      const res = await fetch('/api/v1/telegram/disconnect', { method: 'POST', headers })
      if (res.ok) {
        await checkStatus()
      }
    } catch (err) {
      console.error('Failed to disconnect Telegram:', err)
    } finally {
      setBusy(false)
    }
  }

  const connect = async () => {
    setBusy(true)
    try {
      const headers = { 'Content-Type': 'application/json' }
      const token = getAuthToken()
      if (token) {
        headers['Authorization'] = `Bearer ${token}`
      }
      const res = await fetch('/api/v1/telegram/connect', { method: 'POST', headers })
      if (res.ok) {
        await checkStatus()
      } else {
        const data = await res.json().catch(() => ({}))
        console.error('Failed to connect Telegram:', data.error || res.status)
      }
    } catch (err) {
      console.error('Failed to connect Telegram:', err)
    } finally {
      setBusy(false)
    }
  }

  if (loading) {
    return (
      <div className="flex items-center gap-8px px-12px py-6px bg-white-opacity-6 border border-white-opacity-12 rounded-xl text-0.85em backdrop-blur-8px transition-all duration-300 flex-wrap hover:bg-white-opacity-8 hover:border-white-opacity-16 hover:shadow-glass">
        <div className="flex items-center gap-8px font-medium">
          <span className="w-8px h-8px rounded-full bg-orange-500 shadow-[0_0_16px_rgba(249,115,22,0.5)] animate-pulse-2"></span>
          <span className="text-white font-bold tracking-wide whitespace-nowrap">Telegram: Checking...</span>
        </div>
      </div>
    )
  }

  const canConnect = status.token_configured && !status.enabled
  const canDisconnect = status.enabled

  const stateClass = status.connected ? 'enabled' : status.token_configured ? (status.enabled ? 'disabled' : 'disabled') : 'disabled'
  let label = 'Telegram: Disabled'
  if (!status.token_configured) {
    label = 'Telegram: Not configured'
  } else if (status.connected) {
    label = 'Telegram: Connected'
  } else if (status.enabled) {
    label = 'Telegram: Error'
  } else {
    label = 'Telegram: Disabled'
  }

  const isEnabled = stateClass === 'enabled'
  const isDisabled = stateClass === 'disabled'

  return (
        <div className="flex items-center gap-8px px-12px py-6px bg-white-opacity-6 border border-white-opacity-12 rounded-xl text-0.85em backdrop-blur-8px transition-all duration-300 flex-wrap hover:bg-white-opacity-8 hover:border-white-opacity-16 hover:shadow-glass">
      <div className={`flex items-center gap-6px font-medium`}>
        <span className={`w-8px h-8px rounded-full transition-all duration-300 ${
          isEnabled
            ? 'bg-green-400 shadow-[0_0_16px_rgba(34,197,94,0.6)] animate-pulse-2'
            : 'bg-red-500 shadow-[0_0_16px_rgba(239,68,68,0.6)]'
        }`}></span>
        <span className={`font-bold tracking-wide whitespace-nowrap transition-colors duration-300 ${
          isEnabled ? 'text-green-400' : 'text-red-400'
        }`}>
          {label}
        </span>
      </div>

      <div className="flex items-center">
        {canDisconnect ? (
          <button
            type="button"
            className="px-10px py-5px rounded-lg cursor-pointer font-bold border border-red-500/40 bg-red-500/10 text-white text-0.85em transition-all duration-300 hover:border-red-500/60 hover:bg-red-500/20 hover:scale-105 active:scale-95 disabled:opacity-50 disabled:cursor-not-allowed"
            onClick={disconnect}
            disabled={busy}
            title="Disable Telegram integration"
          >
            Disconnect
          </button>
        ) : (
          <button
            type="button"
            className="px-10px py-5px rounded-lg cursor-pointer font-bold border border-green-400/40 bg-green-400/10 text-white text-0.85em transition-all duration-300 hover:border-green-400/60 hover:bg-green-400/20 hover:scale-105 active:scale-95 disabled:opacity-50 disabled:cursor-not-allowed"
            onClick={connect}
            disabled={busy || !canConnect}
            title={status.token_configured ? 'Enable Telegram integration' : 'TELEGRAM_BOT_TOKEN not configured'}
          >
            Connect
          </button>
        )}
      </div>

      {status.error && !status.connected && (
        <div className="w-full text-red-300 text-0.85em leading-tight whitespace-nowrap overflow-hidden text-ellipsis" title={status.error}>
          {status.error}
        </div>
      )}
    </div>
  )
}

export default TelegramStatus

