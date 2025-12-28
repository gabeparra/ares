import React, { useState, useEffect } from 'react'
import './ProviderSelector.css'

function ProviderSelector({ currentProvider, onProviderChange }) {
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState(null)

  const providers = [
    {
      id: 'local',
      name: 'Ollama (Local)',
      description: 'Local Ollama instance - fast and private',
      icon: '🏠',
      available: true,
    },
    {
      id: 'openrouter',
      name: 'OpenRouter',
      description: 'Cloud-based API - works when Ollama is offline',
      icon: '☁️',
      available: true,
    },
  ]

  useEffect(() => {
    fetchCurrentProvider()
  }, [])

  const fetchCurrentProvider = async () => {
    try {
      const headers = {}
      if (window.authToken) {
        headers['Authorization'] = `Bearer ${window.authToken}`
      }
      const response = await fetch('/api/v1/settings/provider', { headers })
      if (response.ok) {
        const data = await response.json()
        if (data.provider && onProviderChange) {
          onProviderChange(data.provider)
        }
      }
    } catch (err) {
      console.error('Failed to fetch current provider:', err)
    }
  }

  const handleProviderChange = async (providerId) => {
    if (providerId === currentProvider) return

    setLoading(true)
    setError(null)

    try {
      const headers = {
        'Content-Type': 'application/json',
      }
      if (window.authToken) {
        headers['Authorization'] = `Bearer ${window.authToken}`
      }
      const response = await fetch('/api/v1/settings/provider', {
        method: 'POST',
        headers,
        body: JSON.stringify({ provider: providerId }),
      })

      const data = await response.json()

      if (response.ok) {
        if (onProviderChange) {
          onProviderChange(providerId)
        }
      } else {
        const errorMessage = data.error || data.message || `Failed to change provider (${response.status})`
        setError(errorMessage)
        console.error('Provider change failed:', {
          status: response.status,
          statusText: response.statusText,
          error: data.error,
          message: data.message,
          data: data
        })
      }
    } catch (err) {
      const errorMessage = err.message || 'Failed to change provider. Please check your configuration and network connection.'
      setError(errorMessage)
      console.error('Provider change error:', {
        error: err,
        message: err.message,
        stack: err.stack
      })
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="provider-selector">
      <h3>LLM Provider</h3>
      <div className="current-provider">
        <span className="provider-label">Current:</span>
        <span className="provider-name">
          {providers.find(p => p.id === currentProvider)?.name || currentProvider || 'Not set'}
        </span>
      </div>

      {error && (
        <div className="provider-error">{error}</div>
      )}

      <div className="provider-options">
        {providers.map(provider => (
          <button
            key={provider.id}
            className={`provider-button ${currentProvider === provider.id ? 'active' : ''} ${loading ? 'loading' : ''}`}
            onClick={() => handleProviderChange(provider.id)}
            disabled={loading || currentProvider === provider.id || !provider.available}
          >
            <div className="provider-icon">{provider.icon}</div>
            <div className="provider-info">
              <div className="provider-name-text">{provider.name}</div>
              <div className="provider-description">{provider.description}</div>
            </div>
            {currentProvider === provider.id && (
              <div className="provider-check">✓</div>
            )}
          </button>
        ))}
      </div>

      {loading && (
        <div className="provider-loading">
          <span className="spinner"></span>
          Switching provider...
        </div>
      )}
    </div>
  )
}

export default ProviderSelector

