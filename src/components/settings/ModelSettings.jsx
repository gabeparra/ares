import React, { useState, useEffect } from 'react'
import './ModelSettings.css'

function ModelSettings({ currentModel, onModelChange }) {
  const [availableModels, setAvailableModels] = useState([])
  const [loading, setLoading] = useState(false)
  const [selectedModel, setSelectedModel] = useState(currentModel || '')
  const [modelConfig, setModelConfig] = useState({
    temperature: 0.7,
    top_p: 0.9,
    top_k: 40,
    repeat_penalty: 1.1,
  })
  const [systemPrompt, setSystemPrompt] = useState('')
  const [promptLoading, setPromptLoading] = useState(false)

  useEffect(() => {
    loadModels()
    loadPrompt()
  }, [])

  useEffect(() => {
    setSelectedModel(currentModel || '')
  }, [currentModel])

  const loadModels = async () => {
    setLoading(true)
    try {
      const headers = {}
      if (window.authToken) {
        headers['Authorization'] = `Bearer ${window.authToken}`
      }
      const response = await fetch('/api/v1/models', { headers })
      if (response.ok) {
        const data = await response.json()
        setAvailableModels(data.models || [])
      }
    } catch (err) {
      console.error('Failed to load models:', err)
    } finally {
      setLoading(false)
    }
  }

  const loadPrompt = async () => {
    setPromptLoading(true)
    try {
      const response = await fetch('/api/v1/settings/prompt')
      if (response.ok) {
        const data = await response.json()
        setSystemPrompt(data.prompt || '')
      }
    } catch (err) {
      console.error('Failed to load prompt:', err)
    } finally {
      setPromptLoading(false)
    }
  }

  const handleModelChange = (e) => {
    const model = e.target.value
    setSelectedModel(model)
    if (onModelChange) {
      onModelChange(model)
    }
  }

  const handleConfigChange = (key, value) => {
    const numValue = parseFloat(value)
    if (!isNaN(numValue)) {
      setModelConfig(prev => ({
        ...prev,
        [key]: numValue
      }))
    }
  }

  const saveConfig = async () => {
    // TODO: Implement API endpoint to save model configuration
    console.log('Saving model config:', { model: selectedModel, config: modelConfig })
    alert('Model configuration saved (feature coming soon)')
  }

  const savePrompt = async () => {
    setPromptLoading(true)
    try {
      const response = await fetch('/api/v1/settings/prompt', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({ prompt: systemPrompt }),
      })
      if (response.ok) {
        alert('Prompt saved successfully')
      } else {
        const data = await response.json()
        alert(`Failed to save prompt: ${data.error || 'Unknown error'}`)
      }
    } catch (err) {
      console.error('Failed to save prompt:', err)
      alert('Failed to save prompt')
    } finally {
      setPromptLoading(false)
    }
  }

  return (
    <div className="panel model-settings-panel">
      <h2>Model Settings</h2>

      <div className="settings-section">
        <div className="settings-row">
          <label className="setting-label">
            <span>Model</span>
            <select
              value={selectedModel}
              onChange={handleModelChange}
              className="model-select"
              disabled={loading}
            >
              <option value="">Default (llama3.2:3b)</option>
              {availableModels.map((model) => (
                <option key={model} value={model}>
                  {model}
                </option>
              ))}
            </select>
          </label>

          <button
            onClick={loadModels}
            className="refresh-models-btn"
            disabled={loading}
            title="Refresh model list"
            type="button"
          >
            {loading ? 'Loading...' : 'Refresh Models'}
          </button>
        </div>
      </div>

      <div className="settings-section">
        <h3>Generation Parameters</h3>
        
        <label className="setting-label">
          <span>Temperature</span>
          <div className="slider-container">
            <input
              type="range"
              min="0"
              max="2"
              step="0.1"
              value={modelConfig.temperature}
              onChange={(e) => handleConfigChange('temperature', e.target.value)}
              className="slider"
            />
            <span className="slider-value">{modelConfig.temperature}</span>
          </div>
          <small>Controls randomness (0 = deterministic, 2 = very creative)</small>
        </label>

        <label className="setting-label">
          <span>Top P (Nucleus Sampling)</span>
          <div className="slider-container">
            <input
              type="range"
              min="0"
              max="1"
              step="0.05"
              value={modelConfig.top_p}
              onChange={(e) => handleConfigChange('top_p', e.target.value)}
              className="slider"
            />
            <span className="slider-value">{modelConfig.top_p}</span>
          </div>
          <small>Probability mass to consider (0.9 = top 90% of tokens)</small>
        </label>

        <label className="setting-label">
          <span>Top K</span>
          <div className="slider-container">
            <input
              type="range"
              min="0"
              max="100"
              step="1"
              value={modelConfig.top_k}
              onChange={(e) => handleConfigChange('top_k', e.target.value)}
              className="slider"
            />
            <span className="slider-value">{modelConfig.top_k}</span>
          </div>
          <small>Number of top tokens to consider (0 = disabled)</small>
        </label>

        <label className="setting-label">
          <span>Repeat Penalty</span>
          <div className="slider-container">
            <input
              type="range"
              min="0.5"
              max="2"
              step="0.1"
              value={modelConfig.repeat_penalty}
              onChange={(e) => handleConfigChange('repeat_penalty', e.target.value)}
              className="slider"
            />
            <span className="slider-value">{modelConfig.repeat_penalty}</span>
          </div>
          <small>Penalty for repeating tokens (1.0 = no penalty, 2.0 = strong penalty)</small>
        </label>
      </div>

      <div className="settings-section">
        <h3>System Prompt</h3>
        <label className="setting-label">
          <span>Chat System Prompt</span>
          <textarea
            value={systemPrompt}
            onChange={(e) => setSystemPrompt(e.target.value)}
            className="prompt-textarea"
            rows={12}
            placeholder="Enter the system prompt..."
            disabled={promptLoading}
          />
          <small>This prompt defines how the AI assistant behaves in chat conversations</small>
        </label>
        <div className="settings-row settings-row-actions">
          <button
            onClick={loadPrompt}
            className="secondary-btn"
            disabled={promptLoading}
            type="button"
            title="Reload from server"
          >
            Reload
          </button>
          <button
            onClick={savePrompt}
            className="primary-btn"
            disabled={promptLoading}
            type="button"
          >
            {promptLoading ? 'Saving...' : 'Save Prompt'}
          </button>
        </div>
      </div>

      <div className="settings-actions">
        <button
          onClick={saveConfig}
          className="save-config-btn"
          type="button"
        >
          Save Configuration
        </button>
      </div>
    </div>
  )
}

export default ModelSettings

