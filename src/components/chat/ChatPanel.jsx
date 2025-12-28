import React, { useState, useEffect, useRef } from 'react'
import ReactMarkdown from 'react-markdown'
import { Prism as SyntaxHighlighter } from 'react-syntax-highlighter'
import { oneDark } from 'react-syntax-highlighter/dist/esm/styles/prism'
import './ChatPanel.css'

function ChatPanel({ onSendMessage, ws, sessionId: propSessionId, onSessionChange }) {
  // WebSocket is optional - used for real-time updates (Telegram messages, etc.)
  // Chat messages use REST API
  const [messages, setMessages] = useState([])
  const [input, setInput] = useState('')
  const [isTyping, setIsTyping] = useState(false)
  const [selectedFile, setSelectedFile] = useState(null)
  const [availableSessions, setAvailableSessions] = useState([])
  const [availableModels, setAvailableModels] = useState([])
  const [sessionModel, setSessionModel] = useState('')
  const [sessionId, setSessionId] = useState(propSessionId || `session_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`)
  const [isNewSession, setIsNewSession] = useState(!propSessionId)
  const messagesEndRef = useRef(null)
  const inputRef = useRef(null)
  const fileInputRef = useRef(null)
  const sessionIdRef = useRef(sessionId)
  
  // TTS state
  const [ttsPlaying, setTtsPlaying] = useState(null) // index of message being played
  const [ttsAudio, setTtsAudio] = useState(null)
  const [ttsLoading, setTtsLoading] = useState(null) // index of message loading
  const [ttsSettingsOpen, setTtsSettingsOpen] = useState(false)
  const [ttsConfig, setTtsConfig] = useState({
    stability: 0.5,
    similarity_boost: 0.75,
    style: 0.0,
    voice_id: '',
    model_id: 'eleven_multilingual_v2',
    api_configured: false,
  })
  const [ttsVoices, setTtsVoices] = useState([])
  const [ttsConfigLoading, setTtsConfigLoading] = useState(false)
  const [ttsConfigDirty, setTtsConfigDirty] = useState(false)
  const [ttsConfigSaved, setTtsConfigSaved] = useState(false)

  useEffect(() => {
    sessionIdRef.current = sessionId
  }, [sessionId])

  useEffect(() => {
    if (ws) {
      const handleMessage = (event) => {
        const data = JSON.parse(event.data)
        
        if (data.type === 'chat_response') {
          setIsTyping(false)
          setMessages(prev => [...prev, {
            type: 'assistant',
            content: data.response,
            timestamp: new Date(),
          }])
        } else if (data.type === 'telegram_message' || data.type === 'chatgpt_message') {
          // Handle incoming Telegram or ChatGPT messages
          if (data.session_id && data.session_id !== sessionIdRef.current) {
            return
          }
          const messageType = data.role === 'user' ? 'user' : 'assistant'
          const source = data.type === 'telegram_message' ? 'telegram' : 'chatgpt'
          const defaultSender = data.role === 'user' 
            ? (source === 'telegram' ? 'Telegram User' : 'User')
            : 'ARES'
          setMessages(prev => [...prev, {
            type: messageType,
            content: data.message,
            timestamp: new Date(),
            source: source,
            sender: data.sender || defaultSender,
          }])
        }
      }

      ws.addEventListener('message', handleMessage)
      return () => ws.removeEventListener('message', handleMessage)
    }
  }, [ws])

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [messages])

  // Load TTS config and voices on mount
  useEffect(() => {
    const loadTtsConfig = async () => {
      try {
        const headers = {}
        if (window.authToken) {
          headers['Authorization'] = `Bearer ${window.authToken}`
        }
        
        const [configRes, voicesRes] = await Promise.all([
          fetch('/api/v1/tts/config', { headers }),
          fetch('/api/v1/tts/voices', { headers }),
        ])
        
        if (configRes.ok) {
          const config = await configRes.json()
          setTtsConfig(config)
        }
        
        if (voicesRes.ok) {
          const data = await voicesRes.json()
          setTtsVoices(data.voices || [])
        }
      } catch (err) {
        console.error('Failed to load TTS config:', err)
      }
    }
    
    loadTtsConfig()
  }, [])

  const handleFileSelect = (e) => {
    const file = e.target.files[0]
    if (file) {
      setSelectedFile(file)
      setInput(`Please review this file: ${file.name}`)
    }
  }

  const handleFileRemove = () => {
    setSelectedFile(null)
    setInput('')
    if (fileInputRef.current) {
      fileInputRef.current.value = ''
    }
  }

  const readFileContent = (file) => {
    return new Promise((resolve, reject) => {
      const reader = new FileReader()
      reader.onload = (e) => resolve(e.target.result)
      reader.onerror = reject
      reader.readAsText(file)
    })
  }

  // TTS Cache helper functions
  const getCacheKey = (text, voiceId, modelId, stability, similarityBoost, style) => {
    return `tts_${btoa(text).slice(0, 50)}_${voiceId || 'default'}_${modelId}_${stability}_${similarityBoost}_${style}`
  }

  const getCachedAudio = async (cacheKey) => {
    try {
      const cache = await caches.open('tts-audio-cache')
      const cachedResponse = await cache.match(cacheKey)
      if (cachedResponse) {
        const blob = await cachedResponse.blob()
        return URL.createObjectURL(blob)
      }
    } catch (error) {
      console.warn('Cache read error:', error)
    }
    return null
  }

  const cacheAudio = async (cacheKey, blob) => {
    try {
      const cache = await caches.open('tts-audio-cache')
      await cache.put(cacheKey, new Response(blob, {
        headers: { 'Content-Type': 'audio/mpeg' }
      }))
    } catch (error) {
      console.warn('Cache write error:', error)
    }
  }

  // TTS: Play message audio
  const playTTS = async (text, messageIndex) => {
    // Stop any currently playing audio
    if (ttsAudio) {
      ttsAudio.pause()
      ttsAudio.currentTime = 0
      setTtsAudio(null)
      setTtsPlaying(null)
    }
    
    // If clicking on the same message that was playing, just stop
    if (ttsPlaying === messageIndex) {
      return
    }
    
    setTtsLoading(messageIndex)
    
    try {
      // Strip markdown for cleaner speech
      const cleanText = text
        .replace(/```[\s\S]*?```/g, 'code block')
        .replace(/`([^`]+)`/g, '$1')
        .replace(/\*\*([^*]+)\*\*/g, '$1')
        .replace(/\*([^*]+)\*/g, '$1')
        .replace(/#+\s/g, '')
        .replace(/\[([^\]]+)\]\([^)]+\)/g, '$1')
        .replace(/\n+/g, '. ')
        .trim()
      
      // Create cache key
      const cacheKey = getCacheKey(
        cleanText,
        ttsConfig.voice_id || 'default',
        ttsConfig.model_id || 'eleven_multilingual_v2',
        ttsConfig.stability,
        ttsConfig.similarity_boost,
        ttsConfig.style
      )
      
      // Check cache first
      let audioUrl = await getCachedAudio(cacheKey)
      let isFromCache = !!audioUrl
      
      if (!audioUrl) {
        // Not in cache, fetch from API
        const headers = { 'Content-Type': 'application/json' }
        if (window.authToken) {
          headers['Authorization'] = `Bearer ${window.authToken}`
        }
        
        const response = await fetch('/api/v1/tts', {
          method: 'POST',
          headers,
          body: JSON.stringify({
            text: cleanText,
            voice_id: ttsConfig.voice_id || undefined,
            model_id: ttsConfig.model_id || 'eleven_multilingual_v2',
            stability: ttsConfig.stability,
            similarity_boost: ttsConfig.similarity_boost,
            style: ttsConfig.style,
          }),
        })
        
        if (!response.ok) {
          const error = await response.json()
          console.error('TTS error:', error)
          setTtsLoading(null)
          return
        }
        
        const audioBlob = await response.blob()
        audioUrl = URL.createObjectURL(audioBlob)
        
        // Cache the audio for future use
        await cacheAudio(cacheKey, audioBlob)
      }
      
      const audio = new Audio(audioUrl)
      
      audio.onended = () => {
        setTtsPlaying(null)
        setTtsAudio(null)
        // Only revoke URL if it was newly created (not from cache)
        if (!isFromCache) {
          URL.revokeObjectURL(audioUrl)
        }
      }
      
      audio.onerror = () => {
        setTtsPlaying(null)
        setTtsAudio(null)
        if (!isFromCache) {
          URL.revokeObjectURL(audioUrl)
        }
      }
      
      setTtsAudio(audio)
      setTtsPlaying(messageIndex)
      setTtsLoading(null)
      audio.play()
      
    } catch (error) {
      console.error('TTS error:', error)
      setTtsLoading(null)
    }
  }

  // Save TTS configuration
  const saveTtsConfig = async () => {
    setTtsConfigLoading(true)
    setTtsConfigSaved(false)
    try {
      const headers = { 'Content-Type': 'application/json' }
      if (window.authToken) {
        headers['Authorization'] = `Bearer ${window.authToken}`
      }
      
      const configToSave = {
        voice_id: ttsConfig.voice_id,
        model_id: ttsConfig.model_id,
        stability: ttsConfig.stability,
        similarity_boost: ttsConfig.similarity_boost,
        style: ttsConfig.style,
      }
      
      console.log('Saving TTS config:', configToSave)
      
      const response = await fetch('/api/v1/tts/config', {
        method: 'POST',
        headers,
        body: JSON.stringify(configToSave),
      })
      
      if (response.ok) {
        setTtsConfigDirty(false)
        setTtsConfigSaved(true)
        setTimeout(() => setTtsConfigSaved(false), 2000)
      } else {
        console.error('Failed to save TTS config:', await response.text())
      }
    } catch (error) {
      console.error('Failed to save TTS config:', error)
    } finally {
      setTtsConfigLoading(false)
    }
  }
  
  // Update local TTS config and mark as dirty
  const updateTtsConfig = (updates) => {
    setTtsConfig(prev => ({ ...prev, ...updates }))
    setTtsConfigDirty(true)
    setTtsConfigSaved(false)
  }

  const handleSubmit = async (e) => {
    e.preventDefault()
    if (!input.trim() && !selectedFile) return

    let messageContent = input.trim()
    let fileContent = null

    // Handle file upload
    if (selectedFile) {
      try {
        fileContent = await readFileContent(selectedFile)
        if (!messageContent) {
          messageContent = `Please review this ${selectedFile.name} file`
        }
      } catch (error) {
        console.error('Failed to read file:', error)
        setMessages(prev => [...prev, {
          type: 'error',
          content: `Failed to read file: ${error.message}`,
          timestamp: new Date(),
        }])
        return
      }
    }

    const userMessage = {
      type: 'user',
      content: messageContent,
      file: selectedFile ? { name: selectedFile.name, content: fileContent } : null,
      timestamp: new Date(),
    }

    setMessages(prev => [...prev, userMessage])
    setIsTyping(true)

    // Send message via REST API
    try {
      const messageData = {
        message: messageContent,
        session_id: sessionId,
      }

      if (fileContent) {
        messageData.file_content = fileContent
        messageData.file_name = selectedFile.name
      }

      // Include auth token if available
      const headers = {
        'Content-Type': 'application/json',
      }
      if (window.authToken) {
        headers['Authorization'] = `Bearer ${window.authToken}`
      }

      const response = await fetch('/api/v1/chat', {
        method: 'POST',
        headers,
        body: JSON.stringify(messageData),
      })

      if (!response.ok) {
        const errorData = await response.json()
        throw new Error(errorData.error || 'Failed to get response')
      }

      const data = await response.json()
      
      setIsTyping(false)
      setMessages(prev => [...prev, {
        type: 'assistant',
        content: data.response || '',
        timestamp: new Date(),
        model: data.model || null,
        provider: data.provider || null,
      }])
    } catch (error) {
      console.error('Failed to send message:', error)
      setIsTyping(false)
      setMessages(prev => [...prev, {
        type: 'error',
        content: `Error: ${error.message}`,
        timestamp: new Date(),
      }])
    }

    setInput('')
    setSelectedFile(null)
    if (fileInputRef.current) {
      fileInputRef.current.value = ''
    }
    inputRef.current?.focus()
  }

  useEffect(() => {
    // Load available sessions
    const loadSessions = async () => {
      try {
        const headers = {}
        if (window.authToken) {
          headers['Authorization'] = `Bearer ${window.authToken}`
        }
        const response = await fetch('/api/v1/sessions?limit=200', { headers })
        if (response.ok) {
          const data = await response.json()
          const ids = (data.sessions || []).map(s => s.session_id)
          setAvailableSessions(ids)
        }
      } catch (err) {
        console.error('Failed to load sessions:', err)
      }
    }
    loadSessions()
  }, [])

  useEffect(() => {
    const loadModels = async () => {
      try {
        const headers = {}
        if (window.authToken) {
          headers['Authorization'] = `Bearer ${window.authToken}`
        }
        const res = await fetch('/api/v1/models', { headers })
        if (res.ok) {
          const data = await res.json()
          setAvailableModels(data.models || [])
        }
      } catch (err) {
        console.error('Failed to load models:', err)
      }
    }
    loadModels()
  }, [])

  useEffect(() => {
    const loadSessionMeta = async () => {
      try {
        const headers = {}
        if (window.authToken) {
          headers['Authorization'] = `Bearer ${window.authToken}`
        }
        const res = await fetch(`/api/v1/sessions/${encodeURIComponent(sessionId)}`, { headers })
        if (res.ok) {
          const data = await res.json()
          setSessionModel(data.model || '')
        } else {
          setSessionModel('')
        }
      } catch (err) {
        console.error('Failed to load session metadata:', err)
      }
    }
    if (sessionId) loadSessionMeta()
  }, [sessionId])

  const updateSessionModel = async (model) => {
    setSessionModel(model)
    try {
      const headers = { 'Content-Type': 'application/json' }
      if (window.authToken) {
        headers['Authorization'] = `Bearer ${window.authToken}`
      }
      await fetch(`/api/v1/sessions/${encodeURIComponent(sessionId)}`, {
        method: 'PATCH',
        headers,
        body: JSON.stringify({ model: model || null }),
      })
    } catch (err) {
      console.error('Failed to update session model:', err)
    }
  }

  useEffect(() => {
    // Update sessionId when prop changes
    if (propSessionId && propSessionId !== sessionId) {
      setSessionId(propSessionId)
      setIsNewSession(false)
    }
  }, [propSessionId])

  useEffect(() => {
    // Load conversation history when sessionId changes
    const loadHistory = async () => {
      try {
        const headers = {}
        if (window.authToken) {
          headers['Authorization'] = `Bearer ${window.authToken}`
        }
        const response = await fetch(`/api/v1/conversations?session_id=${sessionId}&limit=50`, { headers })
        if (response.ok) {
          const data = await response.json()
          if (data.conversations && data.conversations.length > 0) {
            const historyMessages = data.conversations.map(conv => ({
              type: conv.role === 'user' ? 'user' : 'assistant',
              content: conv.message,
              timestamp: new Date(conv.created_at),
            }))
            setMessages(historyMessages)
            setIsNewSession(false)
          } else {
            setMessages([])
          }
        }
      } catch (err) {
        console.error('Failed to load conversation history:', err)
      }
    }
    
    loadHistory()
  }, [sessionId])

  const handleSessionSelect = (e) => {
    const selectedId = e.target.value
    if (selectedId === 'new') {
      const newSessionId = `session_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`
      setSessionId(newSessionId)
      setIsNewSession(true)
      setMessages([])
      if (onSessionChange) {
        onSessionChange(newSessionId)
      }
    } else if (selectedId && selectedId !== sessionId) {
      setSessionId(selectedId)
      setIsNewSession(false)
      if (onSessionChange) {
        onSessionChange(selectedId)
      }
    }
  }

  const handleNewSession = () => {
    const newSessionId = `session_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`
    setSessionId(newSessionId)
    setIsNewSession(true)
    setMessages([])
    if (onSessionChange) {
      onSessionChange(newSessionId)
    }
  }

  const formatTime = (date) => {
    return new Date(date).toLocaleTimeString()
  }

  const handleReadCodebase = async () => {
    try {
      setIsTyping(true)
      setMessages(prev => [...prev, {
        type: 'user',
        content: 'Please analyze the ARES codebase structure and provide an overview of the main components, architecture, and key files.',
        timestamp: new Date(),
      }])

      // Read key files from the codebase
      const keyFiles = [
        'src/App.jsx',
        'src/main.jsx',
        'api/views.py',
        'api/auth.py',
        'ares_project/settings.py',
        'docker-compose.yml',
      ]

      let codebaseContent = 'ARES Codebase Overview:\n\n'
      
      // For now, we'll send a message asking the AI to analyze the codebase
      // In a real implementation, you'd fetch these files from the server
      const messageContent = `Analyze the ARES codebase. The main files include:
- Frontend: React app in src/ with components for chat, conversations, settings
- Backend: Django REST API in api/ with Auth0 authentication
- Configuration: Docker setup, nginx config, environment variables
- Key features: Chat interface, session management, model selection, transcript processing

Please provide an overview of the architecture and suggest improvements.`

      const headers = {
        'Content-Type': 'application/json',
      }
      if (window.authToken) {
        headers['Authorization'] = `Bearer ${window.authToken}`
      }

      const response = await fetch('/api/v1/chat', {
        method: 'POST',
        headers,
        body: JSON.stringify({
          message: messageContent,
          session_id: sessionId,
        }),
      })

      if (!response.ok) {
        const errorData = await response.json()
        throw new Error(errorData.error || 'Failed to analyze codebase')
      }

      const data = await response.json()
      
      setIsTyping(false)
      setMessages(prev => [...prev, {
        type: 'assistant',
        content: data.response || '',
        timestamp: new Date(),
      }])
    } catch (error) {
      console.error('Failed to read codebase:', error)
      setIsTyping(false)
      setMessages(prev => [...prev, {
        type: 'error',
        content: `Error analyzing codebase: ${error.message}`,
        timestamp: new Date(),
      }])
    }
  }

  return (
    <div className="panel chat-panel">
      <div className="chat-header">
        <h2>Chat with ARES</h2>
        <div className="session-selector-container">
          <select
            value={sessionModel}
            onChange={(e) => updateSessionModel(e.target.value)}
            className="session-selector"
            title="Per-session model"
          >
            <option value="">Model: default</option>
            {availableModels.map((m, index) => (
              <option key={m?.name || index} value={m?.name || ''}>{m?.name || 'Unknown'}</option>
            ))}
          </select>
          <select
            value={isNewSession && !availableSessions.includes(sessionId) ? 'new' : sessionId}
            onChange={handleSessionSelect}
            className="session-selector"
            title="Select conversation session"
          >
            <option value="new">+ New Conversation</option>
            {availableSessions.map((sid) => (
              <option key={sid} value={sid}>
                {sid.replace('session_', '').substring(0, 20)}...
              </option>
            ))}
          </select>
          <button
            onClick={handleNewSession}
            className="new-session-button"
            title="Start new conversation"
          >
            ➕ New
          </button>
          <button
            onClick={() => setTtsSettingsOpen(!ttsSettingsOpen)}
            className={`tts-settings-button ${ttsSettingsOpen ? 'active' : ''}`}
            title="Voice settings"
          >
            🔊
          </button>
        </div>
      </div>
      
      {/* TTS Settings Panel */}
      {ttsSettingsOpen && (
        <div className="tts-settings-panel">
          <div className="tts-settings-header">
            <h3>Voice Settings</h3>
            {!ttsConfig.api_configured && (
              <span className="tts-warning">API key not configured</span>
            )}
          </div>
          
          <div className="tts-setting">
            <label>Voice</label>
            <select
              value={ttsConfig.voice_id || ''}
              onChange={(e) => updateTtsConfig({ voice_id: e.target.value })}
              disabled={!ttsConfig.api_configured}
            >
              <option value="">Default (Rachel)</option>
              {ttsVoices.map(v => (
                <option key={v.voice_id} value={v.voice_id}>
                  {v.name} ({v.category})
                </option>
              ))}
            </select>
          </div>
          
          <div className="tts-setting">
            <label>Model</label>
            <select
              value={ttsConfig.model_id || 'eleven_multilingual_v2'}
              onChange={(e) => updateTtsConfig({ model_id: e.target.value })}
              disabled={!ttsConfig.api_configured}
            >
              <option value="eleven_multilingual_v2">Multilingual v2 (recommended)</option>
              <option value="eleven_turbo_v2_5">Turbo v2.5 (faster)</option>
              <option value="eleven_turbo_v2">Turbo v2</option>
              <option value="eleven_monolingual_v1">Monolingual v1 (legacy)</option>
            </select>
            <span className="tts-setting-hint">v2 models support Style parameter</span>
          </div>
          
          <div className="tts-setting">
            <label>Stability: {ttsConfig.stability.toFixed(2)}</label>
            <input
              type="range"
              min="0"
              max="1"
              step="0.05"
              value={ttsConfig.stability}
              onChange={(e) => updateTtsConfig({ stability: parseFloat(e.target.value) })}
              disabled={!ttsConfig.api_configured}
            />
            <span className="tts-setting-hint">Higher = more consistent, Lower = more expressive</span>
          </div>
          
          <div className="tts-setting">
            <label>Similarity: {ttsConfig.similarity_boost.toFixed(2)}</label>
            <input
              type="range"
              min="0"
              max="1"
              step="0.05"
              value={ttsConfig.similarity_boost}
              onChange={(e) => updateTtsConfig({ similarity_boost: parseFloat(e.target.value) })}
              disabled={!ttsConfig.api_configured}
            />
            <span className="tts-setting-hint">Higher = closer to original voice</span>
          </div>
          
          <div className="tts-setting">
            <label>Style: {ttsConfig.style.toFixed(2)}</label>
            <input
              type="range"
              min="0"
              max="1"
              step="0.05"
              value={ttsConfig.style}
              onChange={(e) => updateTtsConfig({ style: parseFloat(e.target.value) })}
              disabled={!ttsConfig.api_configured}
            />
            <span className="tts-setting-hint">Higher = more expressive style</span>
          </div>
          
          <div className="tts-settings-actions">
            <button
              onClick={saveTtsConfig}
              disabled={!ttsConfigDirty || ttsConfigLoading || !ttsConfig.api_configured}
              className={`tts-save-button ${ttsConfigSaved ? 'saved' : ''}`}
            >
              {ttsConfigLoading ? 'Saving...' : ttsConfigSaved ? 'Saved!' : ttsConfigDirty ? 'Save Settings' : 'No Changes'}
            </button>
            {ttsConfigDirty && (
              <span className="tts-unsaved-hint">Unsaved changes</span>
            )}
          </div>
        </div>
      )}
      
      {isNewSession && messages.length === 0 && (
        <div className="session-info-banner">
          Starting new conversation session: {sessionId.substring(0, 30)}...
        </div>
      )}
      
      <div className="chat-messages">
        {messages.length === 0 ? (
          <div className="empty-state">
            Start a conversation with ARES...
          </div>
        ) : (
          messages.map((msg, idx) => (
            <div key={idx} className={`chat-message ${msg.type}`}>
              <div className="message-header">
                <span className="message-sender">
                  {msg.source === 'telegram' 
                    ? (msg.sender || (msg.type === 'user' ? 'Telegram User' : 'ARES'))
                    : msg.source === 'chatgpt'
                    ? (msg.sender || (msg.type === 'user' ? 'User' : 'ARES'))
                    : (msg.type === 'user' ? 'You' : msg.type === 'error' ? 'Error' : 'ARES')
                  }
                  {msg.source === 'telegram' && ' 📱'}
                  {msg.source === 'chatgpt' && ' 🌐'}
                  {msg.type === 'assistant' && msg.provider && (
                    <span className="message-provider" title={msg.model || ''}>
                      {msg.provider === 'openrouter' ? ' ☁️' : ' 🏠'}
                    </span>
                  )}
                </span>
                <div className="message-actions">
                  {msg.type === 'assistant' && (
                    <button
                      className={`tts-button ${ttsPlaying === idx ? 'playing' : ''} ${ttsLoading === idx ? 'loading' : ''}`}
                      onClick={() => playTTS(msg.content, idx)}
                      title={ttsPlaying === idx ? 'Stop' : 'Read aloud'}
                      disabled={ttsLoading === idx}
                    >
                      {ttsLoading === idx ? '⏳' : ttsPlaying === idx ? '⏹' : '🔊'}
                    </button>
                  )}
                  <span className="message-time">{formatTime(msg.timestamp)}</span>
                </div>
              </div>
              <div className="message-content">
                {msg.type === 'assistant' ? (
                  <ReactMarkdown
                    components={{
                      code({ inline, className, children, ...props }) {
                        const match = /language-(\w+)/.exec(className || '')
                        const codeString = String(children).replace(/\n$/, '')
                        return !inline && match ? (
                          <SyntaxHighlighter
                            style={oneDark}
                            language={match[1]}
                            PreTag="div"
                            customStyle={{
                              margin: '0.5em 0',
                              borderRadius: '6px',
                              fontSize: '0.9em',
                            }}
                            {...props}
                          >
                            {codeString}
                          </SyntaxHighlighter>
                        ) : !inline && codeString.includes('\n') ? (
                          <SyntaxHighlighter
                            style={oneDark}
                            language="text"
                            PreTag="div"
                            customStyle={{
                              margin: '0.5em 0',
                              borderRadius: '6px',
                              fontSize: '0.9em',
                            }}
                            {...props}
                          >
                            {codeString}
                          </SyntaxHighlighter>
                        ) : (
                          <code className="inline-code" {...props}>
                            {children}
                          </code>
                        )
                      },
                      pre({ children }) {
                        return <>{children}</>
                      },
                      p({ children }) {
                        return <p className="markdown-p">{children}</p>
                      },
                      ul({ children }) {
                        return <ul className="markdown-ul">{children}</ul>
                      },
                      ol({ children }) {
                        return <ol className="markdown-ol">{children}</ol>
                      },
                      li({ children }) {
                        return <li className="markdown-li">{children}</li>
                      },
                      h1({ children }) {
                        return <h1 className="markdown-h1">{children}</h1>
                      },
                      h2({ children }) {
                        return <h2 className="markdown-h2">{children}</h2>
                      },
                      h3({ children }) {
                        return <h3 className="markdown-h3">{children}</h3>
                      },
                      blockquote({ children }) {
                        return <blockquote className="markdown-blockquote">{children}</blockquote>
                      },
                      a({ href, children }) {
                        return <a href={href} className="markdown-link" target="_blank" rel="noopener noreferrer">{children}</a>
                      },
                      table({ children }) {
                        return <table className="markdown-table">{children}</table>
                      },
                      th({ children }) {
                        return <th className="markdown-th">{children}</th>
                      },
                      td({ children }) {
                        return <td className="markdown-td">{children}</td>
                      },
                    }}
                  >
                    {msg.content}
                  </ReactMarkdown>
                ) : (
                  msg.content
                )}
                {msg.file && (
                  <div className="file-attachment">
                    <div className="file-info">
                      📎 <strong>{msg.file.name}</strong>
                    </div>
                    <pre className="file-preview">
                      {msg.file.content.length > 1000
                        ? msg.file.content.substring(0, 1000) + '...'
                        : msg.file.content
                      }
                    </pre>
                  </div>
                )}
              </div>
            </div>
          ))
        )}
        
        {isTyping && (
          <div className="chat-message assistant typing">
            <div className="message-header">
              <span className="message-sender">ARES</span>
            </div>
            <div className="typing-indicator">
              <span></span>
              <span></span>
              <span></span>
            </div>
          </div>
        )}
        
        <div ref={messagesEndRef} />
      </div>

      <form onSubmit={handleSubmit} className="chat-input-form">
        {selectedFile && (
          <div className="selected-file">
            <div className="file-info">
              📎 <strong>{selectedFile.name}</strong> ({(selectedFile.size / 1024).toFixed(1)} KB)
            </div>
            <button
              type="button"
              onClick={handleFileRemove}
              className="file-remove-button"
              title="Remove file"
            >
              ✕
            </button>
          </div>
        )}

        <div className="chat-input-container">
          <input
            ref={inputRef}
            type="text"
            value={input}
            onChange={(e) => setInput(e.target.value)}
            placeholder={selectedFile ? "Add a message about the file..." : "Type your message..."}
            className="chat-input"
            disabled={isTyping}
          />
          <input
            ref={fileInputRef}
            type="file"
            onChange={handleFileSelect}
            accept=".py,.js,.jsx,.ts,.tsx,.css,.html,.md,.txt,.json,.xml,.yaml,.yml"
            style={{ display: 'none' }}
            id="file-input"
          />
          <button
            type="button"
            onClick={() => fileInputRef.current?.click()}
            className="file-attach-button"
            title="Attach file for review"
          >
            📎
          </button>
          <button
            type="button"
            onClick={handleReadCodebase}
            className="code-read-button"
            title="Read ARES codebase and bring to chat"
          >
            💻
          </button>
          <button
            type="submit"
            className="chat-send-button"
            disabled={(!input.trim() && !selectedFile) || isTyping}
          >
            Send
          </button>
        </div>
      </form>
    </div>
  )
}

export default ChatPanel

