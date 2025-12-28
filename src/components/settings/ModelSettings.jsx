import React, { useState, useEffect } from 'react'
import './ModelSettings.css'

function ModelSettings({ currentModel, onModelChange, currentProvider: propProvider }) {
  const [availableModels, setAvailableModels] = useState([])
  const [loading, setLoading] = useState(false)
  const [modelLoading, setModelLoading] = useState(false)
  const [activeModel, setActiveModel] = useState('')
  const [selectedModel, setSelectedModel] = useState('')
  const [modelLoaded, setModelLoaded] = useState(false)
  const [modelError, setModelError] = useState(null)
  const [currentProvider, setCurrentProvider] = useState(propProvider || 'local')
  const [modelConfig, setModelConfig] = useState({
    temperature: 0.7,
    top_p: 0.9,
    top_k: 40,
    repeat_penalty: 1.1,
  })
  const [systemPrompt, setSystemPrompt] = useState('')
  const [promptLoading, setPromptLoading] = useState(false)
  const [restartingBackend, setRestartingBackend] = useState(false)
  const [restartingFrontend, setRestartingFrontend] = useState(false)
  const [agentConfig, setAgentConfig] = useState({
    agent_url: '',
    agent_api_key: '',
    agent_enabled: false,
  })
  const [agentLoading, setAgentLoading] = useState(false)

  useEffect(() => {
    if (propProvider) {
      setCurrentProvider(propProvider)
    } else {
      loadProvider()
    }
    loadPrompt()
    loadModelConfig()
    loadAgentConfig()
  }, [])

  useEffect(() => {
    // Update local state when prop changes
    if (propProvider && propProvider !== currentProvider) {
      setCurrentProvider(propProvider)
    }
  }, [propProvider])

  useEffect(() => {
    // Reload models when provider changes
    if (currentProvider) {
      console.log('[ModelSettings] Provider changed to:', currentProvider, '- reloading models')
      loadModels()
    }
  }, [currentProvider])

  const loadProvider = async () => {
    try {
      const headers = {}
      if (window.authToken) {
        headers['Authorization'] = `Bearer ${window.authToken}`
      }
      const response = await fetch('/api/v1/settings/provider', { headers })
      if (response.ok) {
        const data = await response.json()
        setCurrentProvider(data.provider || 'local')
      }
    } catch (err) {
      console.error('Failed to load provider:', err)
    }
  }

  const loadModels = async () => {
    setLoading(true)
    setModelError(null)
    try {
      const headers = {}
      if (window.authToken) {
        headers['Authorization'] = `Bearer ${window.authToken}`
      }
      
      if (currentProvider === 'openrouter') {
        // Load OpenRouter models
        const [modelsRes, currentRes] = await Promise.all([
          fetch('/api/v1/settings/openrouter-models', { headers }),
          fetch('/api/v1/settings/openrouter-model', { headers })
        ])
        
        if (modelsRes.ok && currentRes.ok) {
          const modelsData = await modelsRes.json()
          const currentData = await currentRes.json()
          const models = modelsData.models || []
          setAvailableModels(models.map(m => ({
            name: m.id,
            full_name: m.name,
            description: m.description
          })))
          setActiveModel(currentData.model || '')
          setSelectedModel(currentData.model || '')
          setModelLoaded(true)
          
          if (onModelChange && currentData.model) {
            onModelChange(currentData.model)
          }
        } else {
          setModelError('Failed to load OpenRouter models')
        }
      } else {
        // Load Ollama models (existing behavior)
        const response = await fetch('/api/v1/models', { headers })
        const data = await response.json()
        if (response.ok) {
          const models = data.models || []
          setAvailableModels(models)
          setActiveModel(data.current_model || '')
          setModelLoaded(data.model_loaded || false)
          
          // Find the short name that matches the current full model name
          const currentFullName = data.current_model || ''
          const matchingModel = models.find(m => m.full_name === currentFullName)
          setSelectedModel(matchingModel ? matchingModel.name : '')
          
          if (onModelChange && data.current_model) {
            onModelChange(data.current_model)
          }
        } else {
          setModelError(data.error || 'Failed to load models')
        }
      }
    } catch (err) {
      console.error('Failed to load models:', err)
      setModelError('Failed to connect to API')
    } finally {
      setLoading(false)
    }
  }

  const switchModel = async (modelName) => {
    if (!modelName) return
    
    // Check if the selected model is already active
    if (currentProvider === 'openrouter') {
      if (modelName === activeModel) return
    } else {
      const matchingModel = availableModels.find(m => m.name === modelName)
      if (matchingModel && matchingModel.full_name === activeModel) return
    }
    
    setModelLoading(true)
    setModelError(null)
    try {
      const headers = {
        'Content-Type': 'application/json',
      }
      if (window.authToken) {
        headers['Authorization'] = `Bearer ${window.authToken}`
      }
      
      let response
      if (currentProvider === 'openrouter') {
        response = await fetch('/api/v1/settings/openrouter-model', {
          method: 'POST',
          headers,
          body: JSON.stringify({ model: modelName }),
        })
      } else {
        response = await fetch('/api/v1/models', {
          method: 'POST',
          headers,
          body: JSON.stringify({ model: modelName }),
        })
      }
      
      const data = await response.json()
      if (response.ok) {
        // Refresh models to get updated state
        await loadModels()
        alert(data.message || 'Model changed successfully')
      } else {
        setModelError(data.error || 'Failed to change model')
        alert(`Failed to change model: ${data.error || 'Unknown error'}`)
      }
    } catch (err) {
      console.error('Failed to switch model:', err)
      setModelError('Failed to switch model')
      alert('Failed to switch model')
    } finally {
      setModelLoading(false)
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

  const loadModelConfig = async () => {
    try {
      const headers = {}
      if (window.authToken) {
        headers['Authorization'] = `Bearer ${window.authToken}`
      }
      const response = await fetch('/api/v1/settings/model-config', { headers })
      if (response.ok) {
        const data = await response.json()
        if (data.config) {
          setModelConfig(prev => ({
            ...prev,
            ...data.config
          }))
        }
      }
    } catch (err) {
      console.error('Failed to load model config:', err)
    }
  }

  const handleModelChange = (e) => {
    const model = e.target.value
    setSelectedModel(model)
  }

  const handleLoadModel = () => {
    if (selectedModel) {
      switchModel(selectedModel)
    }
  }

  // Check if the selected model is already the active one
  const isSelectedModelActive = () => {
    if (!selectedModel || !activeModel) return false
    if (currentProvider === 'openrouter') {
      return selectedModel === activeModel
    }
    const matchingModel = availableModels.find(m => m.name === selectedModel)
    return matchingModel && matchingModel.full_name === activeModel
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
    setLoading(true)
    try {
      const headers = {
        'Content-Type': 'application/json',
      }
      if (window.authToken) {
        headers['Authorization'] = `Bearer ${window.authToken}`
      }
      const response = await fetch('/api/v1/settings/model-config', {
        method: 'POST',
        headers,
        body: JSON.stringify({ config: modelConfig }),
      })
      if (response.ok) {
        alert('Model configuration saved successfully')
      } else {
        const data = await response.json()
        alert(`Failed to save configuration: ${data.error || 'Unknown error'}`)
      }
    } catch (err) {
      console.error('Failed to save model config:', err)
      alert('Failed to save configuration')
    } finally {
      setLoading(false)
    }
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

  const loadAgentConfig = async () => {
    try {
      const headers = {}
      if (window.authToken) {
        headers['Authorization'] = `Bearer ${window.authToken}`
      }
      const response = await fetch('/api/v1/settings/agent', { headers })
      if (response.ok) {
        const data = await response.json()
        setAgentConfig({
          agent_url: data.agent_url || '',
          agent_api_key: data.agent_api_key || '',
          agent_enabled: data.agent_enabled || false,
        })
      }
    } catch (err) {
      console.error('Failed to load agent config:', err)
    }
  }

  const saveAgentConfig = async () => {
    setAgentLoading(true)
    try {
      const headers = {
        'Content-Type': 'application/json',
      }
      if (window.authToken) {
        headers['Authorization'] = `Bearer ${window.authToken}`
      }
      const response = await fetch('/api/v1/settings/agent', {
        method: 'POST',
        headers,
        body: JSON.stringify(agentConfig),
      })
      if (response.ok) {
        alert('Agent configuration saved successfully')
      } else {
        const data = await response.json()
        alert(`Failed to save agent configuration: ${data.error || 'Unknown error'}`)
      }
    } catch (err) {
      console.error('Failed to save agent config:', err)
      alert('Failed to save agent configuration')
    } finally {
      setAgentLoading(false)
    }
  }

  const handleAgentConfigChange = (key, value) => {
    setAgentConfig(prev => ({
      ...prev,
      [key]: value
    }))
  }

  const restartService = async (service) => {
    console.log(`[RestartService] Called with service: ${service}`)
    const setRestarting = service === 'backend' ? setRestartingBackend : setRestartingFrontend
    
    const confirmed = window.confirm(
      `Are you sure you want to restart the ${service}? ${service === 'frontend' ? 'The page will reload.' : 'This may briefly interrupt service.'}`
    )
    
    if (!confirmed) {
      console.log('[RestartService] User cancelled')
      return
    }
    
    setRestarting(true)
    console.log('[RestartService] User confirmed, making request...')
    console.log('[RestartService] Auth token present:', !!window.authToken)
    
    try {
      const headers = {
        'Content-Type': 'application/json',
      }
      if (window.authToken) {
        headers['Authorization'] = `Bearer ${window.authToken}`
      }
      
      console.log('[RestartService] Sending POST to /api/v1/services/restart')
      const response = await fetch('/api/v1/services/restart', {
        method: 'POST',
        headers,
        body: JSON.stringify({ service }),
      })
      
      console.log('[RestartService] Response status:', response.status)
      const data = await response.json()
      console.log('[RestartService] Response data:', data)
      
      if (response.ok) {
        alert(data.message || `${service} is restarting`)
        if (service === 'frontend') {
          setTimeout(() => window.location.reload(), 3000)
        }
      } else {
        alert(`Failed to restart ${service}: ${data.error || 'Unknown error'}`)
      }
    } catch (err) {
      console.error(`[RestartService] Error:`, err)
      alert(`Failed to restart ${service}: ${err.message}`)
    } finally {
      setRestarting(false)
    }
  }

  return (
    <div className="panel model-settings-panel">
      <h2>Model Settings</h2>

      <div className="settings-section">
        <h3>AI Model</h3>
        
        <div className="model-status">
          <span className="status-label">Provider:</span>
          <span className="status-value">{currentProvider === 'openrouter' ? 'OpenRouter' : 'Ollama (Local)'}</span>
        </div>
        
        <div className="model-status">
          <span className="status-label">Current Model:</span>
          <span className={`status-value ${modelLoaded ? 'loaded' : 'not-loaded'}`}>
            {activeModel || 'None'}
            {modelLoaded && <span className="status-badge">Active</span>}
          </span>
        </div>

        {modelError && (
          <div className="model-error">{modelError}</div>
        )}

        <div className="settings-row">
          <label className="setting-label">
            <span>Switch Model</span>
            <select
              value={selectedModel}
              onChange={handleModelChange}
              className="model-select"
              disabled={loading || modelLoading}
            >
              <option value="">Select a model...</option>
              {availableModels.map((model, index) => (
                <option key={model?.name || index} value={model?.name || ''}>
                  {currentProvider === 'openrouter' 
                    ? `${model?.full_name || model?.name || 'Unknown'}${model?.description ? ` - ${model.description}` : ''}`
                    : `${model?.name || 'Unknown'} (${model?.full_name || 'Unknown'})`}
                </option>
              ))}
            </select>
          </label>

          <button
            onClick={handleLoadModel}
            className="load-model-btn"
            disabled={loading || modelLoading || !selectedModel || (currentProvider === 'openrouter' ? selectedModel === activeModel : isSelectedModelActive())}
            title={currentProvider === 'openrouter' ? 'Switch to selected model' : 'Load selected model'}
            type="button"
          >
            {modelLoading ? (currentProvider === 'openrouter' ? 'Switching...' : 'Loading Model...') : (currentProvider === 'openrouter' ? 'Switch Model' : 'Load Model')}
          </button>

          <button
            onClick={loadModels}
            className="refresh-models-btn"
            disabled={loading || modelLoading}
            title="Refresh model list"
            type="button"
          >
            {loading ? 'Refreshing...' : 'Refresh'}
          </button>
        </div>
        
        <small>
          {currentProvider === 'openrouter' 
            ? 'OpenRouter models are cloud-based and switch instantly. No local loading required.'
            : 'Loading a different model may take a minute. The 7B models require more GPU memory.'}
        </small>
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

      <div className="settings-section">
        <h3>ARES Agent (4090 Rig)</h3>
        <p className="section-description">
          Configure connection to the ARES Agent running on your local machine for GPU control.
        </p>
        
        <label className="setting-label">
          <span>Agent URL</span>
          <input
            type="text"
            value={agentConfig.agent_url}
            onChange={(e) => handleAgentConfigChange('agent_url', e.target.value)}
            className="agent-input"
            placeholder="http://100.x.x.x:8100"
            disabled={agentLoading}
          />
          <small>URL to the ARES Agent (e.g., Tailscale IP or localhost)</small>
        </label>

        <label className="setting-label">
          <span>Agent API Key</span>
          <input
            type="password"
            value={agentConfig.agent_api_key}
            onChange={(e) => handleAgentConfigChange('agent_api_key', e.target.value)}
            className="agent-input"
            placeholder="Enter shared secret"
            disabled={agentLoading}
          />
          <small>Shared secret for agent authentication</small>
        </label>

        <label className="setting-label checkbox-label">
          <input
            type="checkbox"
            checked={agentConfig.agent_enabled}
            onChange={(e) => handleAgentConfigChange('agent_enabled', e.target.checked)}
            disabled={agentLoading}
          />
          <span>Enable Agent</span>
        </label>

        <div className="settings-row settings-row-actions">
          <button
            onClick={loadAgentConfig}
            className="secondary-btn"
            disabled={agentLoading}
            type="button"
          >
            Reload
          </button>
          <button
            onClick={saveAgentConfig}
            className="primary-btn"
            disabled={agentLoading}
            type="button"
          >
            {agentLoading ? 'Saving...' : 'Save Agent Config'}
          </button>
        </div>
      </div>

      <div className="settings-section danger-section">
        <h3>Service Controls</h3>
        <p className="section-description">
          Restart services when configuration changes require a full reload.
        </p>
        <div className="service-controls">
          <button
            onClick={() => restartService('backend')}
            className="restart-btn restart-backend"
            disabled={restartingBackend || restartingFrontend}
            type="button"
          >
            {restartingBackend ? 'Restarting...' : 'Restart Backend'}
          </button>
          <button
            onClick={() => restartService('frontend')}
            className="restart-btn restart-frontend"
            disabled={restartingBackend || restartingFrontend}
            type="button"
          >
            {restartingFrontend ? 'Restarting...' : 'Restart Frontend'}
          </button>
        </div>
        <small className="danger-note">These actions will briefly interrupt the respective service.</small>
      </div>
    </div>
  )
}

export default ModelSettings

