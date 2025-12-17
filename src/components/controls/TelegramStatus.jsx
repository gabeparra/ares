import React, { useState, useEffect } from 'react'
import './TelegramStatus.css'

function TelegramStatus() {
  const [enabled, setEnabled] = useState(false)
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    checkStatus()
  }, [])

  const checkStatus = async () => {
    setLoading(true)
    try {
      const response = await fetch('/api/health')
      if (response.ok) {
        const data = await response.json()
        setEnabled(data.telegram_notifications === 'enabled')
      }
    } catch (err) {
      console.error('Failed to check Telegram status:', err)
    } finally {
      setLoading(false)
    }
  }

  if (loading) {
    return (
      <div className="telegram-status">
        <span className="telegram-indicator checking">Checking...</span>
      </div>
    )
  }

  return (
    <div className="telegram-status">
      <span className={`telegram-indicator ${enabled ? 'enabled' : 'disabled'}`}>
        {enabled ? '📱 Telegram Connected' : '📱 Telegram Disabled'}
      </span>
    </div>
  )
}

export default TelegramStatus

