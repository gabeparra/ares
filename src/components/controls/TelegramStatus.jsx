import React, { useState, useEffect } from 'react'
import './TelegramStatus.css'

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
      if (window.authToken) {
        headers['Authorization'] = `Bearer ${window.authToken}`
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
      if (window.authToken) {
        headers['Authorization'] = `Bearer ${window.authToken}`
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
      if (window.authToken) {
        headers['Authorization'] = `Bearer ${window.authToken}`
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
      <div className="telegram-status">
        <div className="telegram-indicator checking">
          <span className="telegram-dot"></span>
          <span className="telegram-text">Telegram: Checking...</span>
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

  return (
    <div className="telegram-status">
      <div className={`telegram-indicator ${stateClass}`}>
        <span className="telegram-dot"></span>
        <span className="telegram-text">
          {label}
        </span>
      </div>

      <div className="telegram-actions">
        {canDisconnect ? (
          <button
            type="button"
            className="telegram-btn telegram-btn-danger"
            onClick={disconnect}
            disabled={busy}
            title="Disable Telegram integration"
          >
            Disconnect
          </button>
        ) : (
          <button
            type="button"
            className="telegram-btn telegram-btn-primary"
            onClick={connect}
            disabled={busy || !canConnect}
            title={status.token_configured ? 'Enable Telegram integration' : 'TELEGRAM_BOT_TOKEN not configured'}
          >
            Connect
          </button>
        )}
      </div>

      {status.error && !status.connected && (
        <div className="telegram-error" title={status.error}>
          {status.error}
        </div>
      )}
    </div>
  )
}

export default TelegramStatus

