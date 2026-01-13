import React, { useState, useEffect, useRef } from 'react'
import ReactMarkdown from 'react-markdown'
import { Prism as SyntaxHighlighter } from 'react-syntax-highlighter'
import { oneDark } from 'react-syntax-highlighter/dist/esm/styles/prism'
import { safeJsonParse } from '../../services/api'
import { getAuthToken } from '../../services/auth'

// Helper function to generate daily session ID (YYYY-MM-DD format)
function getDailySessionId() {
  const today = new Date()
  const year = today.getFullYear()
  const month = String(today.getMonth() + 1).padStart(2, '0')
  const day = String(today.getDate()).padStart(2, '0')
  return `daily_${year}-${month}-${day}`
}

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
  const [sessionId, setSessionId] = useState(propSessionId || getDailySessionId())
  const [isNewSession, setIsNewSession] = useState(!propSessionId)
  const messagesEndRef = useRef(null)
  const inputRef = useRef(null)
  const fileInputRef = useRef(null)
  const sessionIdRef = useRef(sessionId)
  const recognitionRef = useRef(null) // For Web Speech API fallback
  const mediaRecorderRef = useRef(null) // For Whisper-based recording
  const audioChunksRef = useRef([])
  const audioContextRef = useRef(null) // For silence detection
  const analyserRef = useRef(null) // For silence detection
  const silenceDetectionRef = useRef(null) // Interval for checking silence
  const lastSoundTimeRef = useRef(Date.now()) // Track when we last heard sound
  const speechTextStartRef = useRef('') // Store input value when speech starts
  const silenceTimeoutRef = useRef(null)
  const isVoiceModeRef = useRef(false) // Track if we're in voice mode (auto-send + auto-TTS)
  const [isVoiceMode, setIsVoiceMode] = useState(false) // State for UI display
  const isTtsPlayingRef = useRef(false) // Track if TTS is currently playing (to prevent feedback)
  
  // Speech recognition state
  const [isListening, setIsListening] = useState(false)
  const isListeningRef = useRef(false) // Ref to track listening state for closures
  const [isTranscribing, setIsTranscribing] = useState(false) // Whisper processing
  const [isSpeechSupported, setIsSpeechSupported] = useState(false)
  const [useWhisper, setUseWhisper] = useState(true) // Use Whisper by default
  const [whisperConfigured, setWhisperConfigured] = useState(false)
  const [speechError, setSpeechError] = useState(null)
  const [speechLanguage, setSpeechLanguage] = useState('') // Empty = auto-detect for Whisper
  
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
  // Volume is stored locally (not synced to server) - defaults to 0.8
  const [ttsVolume, setTtsVolume] = useState(() => {
    const stored = localStorage.getItem('ares_tts_volume')
    return stored !== null ? parseFloat(stored) : 0.8
  })
  const [ttsVoices, setTtsVoices] = useState([])
  const [ttsConfigLoading, setTtsConfigLoading] = useState(false)
  const [ttsConfigDirty, setTtsConfigDirty] = useState(false)
  const [ttsConfigSaved, setTtsConfigSaved] = useState(false)

  useEffect(() => {
    sessionIdRef.current = sessionId
  }, [sessionId])

  // Function to start silence timeout (called on speech detection)
  // Define this early so it can be used in useEffect hooks
  const startSilenceTimeout = React.useCallback(() => {
    // Clear existing timeout first
    if (silenceTimeoutRef.current) {
      clearTimeout(silenceTimeoutRef.current)
      silenceTimeoutRef.current = null
    }
    
    // Only set timeout if we're listening, have input text, and TTS is not playing
    if (isListening && input.trim() && !isTtsPlayingRef.current) {
      silenceTimeoutRef.current = setTimeout(() => {
        // Auto-submit after 4 seconds of silence
        // Check current values at timeout execution - use refs to get current state
        const currentInput = inputRef.current?.value || ''
        const stillListening = isListeningRef.current
        console.log('Silence timeout triggered, input:', currentInput, 'voiceMode:', isVoiceModeRef.current, 'stillListening:', stillListening)
        
        // Only auto-submit if we're still listening and in voice mode
        if (currentInput.trim() && stillListening && isVoiceModeRef.current && !isTtsPlayingRef.current) {
          // Stop recognition first
          if (recognitionRef.current) {
            try {
              recognitionRef.current.stop()
            } catch (e) {
              // Ignore
            }
          }
          
          // Trigger form submission by clicking submit button
          const form = inputRef.current?.closest('form')
          if (form) {
            const submitButton = form.querySelector('button[type="submit"]')
            if (submitButton && !submitButton.disabled) {
              console.log('Auto-submitting message')
              submitButton.click()
            }
          }
        }
      }, 4000) // 4 seconds
    }
  }, [isListening, input])

  // Handle silence timeout when input changes while listening
  useEffect(() => {
    if (isListening && isVoiceModeRef.current && input.trim()) {
      startSilenceTimeout()
    } else if (!isListening && silenceTimeoutRef.current) {
      // Clear timeout if we stop listening
      if (silenceTimeoutRef.current) {
        clearTimeout(silenceTimeoutRef.current)
        silenceTimeoutRef.current = null
      }
    }
    
    // Cleanup on unmount
    return () => {
      if (silenceTimeoutRef.current) {
        clearTimeout(silenceTimeoutRef.current)
        silenceTimeoutRef.current = null
      }
    }
  }, [input, isListening, startSilenceTimeout])

  // Check if Whisper API is configured
  useEffect(() => {
    const checkWhisperConfig = async () => {
      try {
        const headers = {}
        const token = getAuthToken()
        if (token) {
          headers['Authorization'] = `Bearer ${token}`
        }
        const response = await fetch('/api/v1/stt/config', { headers })
        if (response.ok) {
          const data = await response.json()
          setWhisperConfigured(data.api_configured)
          if (!data.api_configured) {
            console.warn('Whisper API not configured, will fall back to Web Speech API')
            setUseWhisper(false)
          }
        }
      } catch (error) {
        console.error('Failed to check Whisper config:', error)
        setUseWhisper(false)
      }
    }
    checkWhisperConfig()
  }, [])

  // Initialize speech recognition (MediaRecorder for Whisper, or Web Speech API fallback)
  useEffect(() => {
    // Check for MediaRecorder support (for Whisper)
    const supportsMediaRecorder = 'MediaRecorder' in window && navigator.mediaDevices?.getUserMedia
    
    // Check for Web Speech API support (fallback)
    const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition
    
    if (!supportsMediaRecorder && !SpeechRecognition) {
      setIsSpeechSupported(false)
      console.warn('Neither MediaRecorder nor Speech recognition supported in this browser')
      return
    }
    
    setIsSpeechSupported(true)
    
    // Set up Web Speech API as fallback (only if Whisper not configured or not available)
    if (SpeechRecognition && !useWhisper) {
      try {
        const recognition = new SpeechRecognition()
        recognition.continuous = true
        recognition.interimResults = true
        
        recognition.onstart = () => {
          isListeningRef.current = true
          setIsListening(true)
          setSpeechError(null)
          // Don't automatically enable voice mode - only enable it explicitly
        }
        
        recognition.onresult = (event) => {
          // Only process results if we're still listening
          if (!isListeningRef.current) {
            return
          }
          
          let interimTranscript = ''
          let allFinalTranscript = ''
          
          for (let i = 0; i < event.results.length; i++) {
            const transcript = event.results[i][0].transcript
            if (event.results[i].isFinal) {
              allFinalTranscript += transcript + ' '
            } else {
              interimTranscript = transcript
            }
          }
          
          // Check again after processing (in case state changed during processing)
          if (!isListeningRef.current) {
            return
          }
          
          startSilenceTimeout()
          
          const baseText = speechTextStartRef.current
          let speechText = allFinalTranscript.trim()
          if (interimTranscript) {
            speechText += (speechText ? ' ' : '') + interimTranscript
          }
          
          const combined = (baseText.trim() + ' ' + speechText.trim()).trim()
          setInput(combined)
        }
        
        recognition.onerror = (event) => {
          console.error('Speech recognition error:', event.error)
          isListeningRef.current = false
          setIsListening(false)
          
          let errorMessage = 'Speech recognition error'
          switch (event.error) {
            case 'no-speech':
              errorMessage = 'No speech detected. Try again.'
              break
            case 'audio-capture':
              errorMessage = 'No microphone found. Please check your microphone.'
              break
            case 'not-allowed':
              errorMessage = 'Microphone permission denied. Please allow microphone access.'
              break
            case 'network':
              errorMessage = 'Network error. Please check your connection.'
              break
            case 'aborted':
              return
            default:
              errorMessage = `Error: ${event.error}`
          }
          
          setSpeechError(errorMessage)
          setTimeout(() => setSpeechError(null), 5000)
        }
        
        recognition.onend = () => {
          isListeningRef.current = false
          setIsListening(false)
          if (silenceTimeoutRef.current) {
            clearTimeout(silenceTimeoutRef.current)
            silenceTimeoutRef.current = null
          }
          
          if (isVoiceModeRef.current && recognitionRef.current && !isTtsPlayingRef.current) {
            setTimeout(() => {
              if (isVoiceModeRef.current && recognitionRef.current && !isTtsPlayingRef.current) {
                try {
                  recognitionRef.current.lang = speechLanguage || 'en-US'
                  speechTextStartRef.current = ''
                  recognitionRef.current.start()
                } catch (error) {
                  if (error.name !== 'InvalidStateError') {
                    console.log('Auto-restart recognition on end:', error)
                  }
                }
              }
            }, 300)
          }
        }
        
        recognitionRef.current = recognition
      } catch (error) {
        console.error('Failed to initialize speech recognition:', error)
      }
    }
    
    return () => {
      // Clean up Web Speech API
      if (recognitionRef.current) {
        try {
          recognitionRef.current.stop()
        } catch (e) {
          // Ignore errors when cleaning up
        }
        recognitionRef.current = null
      }
      // Clean up MediaRecorder
      if (mediaRecorderRef.current && mediaRecorderRef.current.state !== 'inactive') {
        try {
          mediaRecorderRef.current.stop()
        } catch (e) {
          // Ignore errors when cleaning up
        }
      }
      // Clean up silence detection
      if (silenceDetectionRef.current) {
        clearInterval(silenceDetectionRef.current)
        silenceDetectionRef.current = null
      }
      if (audioContextRef.current) {
        try {
          audioContextRef.current.close()
        } catch (e) {
          // Ignore errors when cleaning up
        }
        audioContextRef.current = null
      }
    }
  }, [useWhisper])

  useEffect(() => {
    if (ws) {
      const handleMessage = (event) => {
        const data = JSON.parse(event.data)
        
        if (data.type === 'chat_response') {
          setIsTyping(false)
          const assistantMessage = {
            type: 'assistant',
            content: data.response,
            timestamp: new Date(),
          }
          setMessages(prev => {
            const newMessages = [...prev, assistantMessage]
            // Auto-play TTS if in voice mode
            if (isVoiceModeRef.current && data.response && ttsConfig.api_configured) {
              setTimeout(() => {
                const messageIndex = newMessages.length - 1
                playTTS(data.response, messageIndex)
              }, 300)
            }
            return newMessages
          })
          // Keep voice mode active - don't clear it so conversation continues
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
        const token = getAuthToken()
        if (token) {
          headers['Authorization'] = `Bearer ${token}`
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
      isTtsPlayingRef.current = false
      return
    }
    
    // Stop speech recognition while TTS is playing to prevent feedback loop
    isTtsPlayingRef.current = true
    if (recognitionRef.current && isListening) {
      try {
        recognitionRef.current.stop()
      } catch (e) {
        // Ignore errors
      }
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
      let audio = null
      
      if (!audioUrl) {
        // Not in cache, fetch from API with streaming
        const headers = { 'Content-Type': 'application/json' }
        const token = getAuthToken()
        if (token) {
          headers['Authorization'] = `Bearer ${token}`
        }
        
        // Set a timeout for the entire streaming process
        const streamTimeout = setTimeout(() => {
          console.error('TTS streaming timeout - resetting state')
          setTtsLoading(null)
          setTtsPlaying(null)
          setTtsAudio(null)
          isTtsPlayingRef.current = false
        }, 60000) // 60 second timeout
        
        try {
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
              stream: true, // Enable streaming
            }),
          })
          
          if (!response.ok) {
            clearTimeout(streamTimeout)
            // Try to parse error
            try {
              const errorText = await response.text()
              const error = JSON.parse(errorText)
              console.error('TTS error:', error)
            } catch {
              console.error('TTS error: HTTP', response.status)
            }
            setTtsLoading(null)
            isTtsPlayingRef.current = false
            return
          }
          
          // Collect all chunks first for reliable playback
          // This provides lower latency than non-streaming (backend streams to us)
          // while ensuring reliable audio playback
          const reader = response.body.getReader()
          const chunks = []
          
          while (true) {
            const { done, value } = await reader.read()
            
            if (done) {
              break
            }
            
            chunks.push(value)
          }
          
          clearTimeout(streamTimeout)
          
          if (chunks.length === 0) {
            console.error('TTS error: No audio data received')
            setTtsLoading(null)
            isTtsPlayingRef.current = false
            return
          }
          
          // Create blob from all chunks
          const audioBlob = new Blob(chunks, { type: 'audio/mpeg' })
          audioUrl = URL.createObjectURL(audioBlob)
          
          // Cache the audio for future use
          await cacheAudio(cacheKey, audioBlob)
          
          // Create audio element
          audio = new Audio(audioUrl)
          
        } catch (error) {
          clearTimeout(streamTimeout)
          console.error('TTS streaming error:', error)
          setTtsLoading(null)
          isTtsPlayingRef.current = false
          return
        }
      } else {
        // From cache - create audio normally
        audio = new Audio(audioUrl)
      }
      
      // Helper function to clean up TTS state
      const cleanupTts = () => {
        setTtsPlaying(null)
        setTtsAudio(null)
        isTtsPlayingRef.current = false
        // Only revoke URL if it was newly created (not from cache)
        if (!isFromCache && audioUrl) {
          URL.revokeObjectURL(audioUrl)
        }
      }
      
      // Helper function to restart voice recognition after TTS ends
      // Only restarts if voice mode is explicitly enabled (not just when mic is used)
      const restartVoiceRecognition = () => {
        // Only auto-restart if voice mode was explicitly enabled
        // Voice mode should be enabled separately, not automatically when mic is used
        if (isVoiceModeRef.current && !isTtsPlayingRef.current) {
          setTimeout(() => {
            if (isVoiceModeRef.current && !isTtsPlayingRef.current && isListeningRef.current === false) {
              // Reset speech text for new input
              speechTextStartRef.current = ''
              // Start listening again (works for both Whisper and Web Speech API)
              startListening()
            }
          }, 500) // Give a small delay before restarting
        }
      }
      
      // Set up event handlers
      audio.onended = () => {
        cleanupTts()
        restartVoiceRecognition()
      }
      
      audio.onerror = (e) => {
        console.error('Audio playback error:', e)
        cleanupTts()
      }
      
      // Also listen for stalled/waiting events to detect issues
      audio.onstalled = () => {
        console.warn('Audio playback stalled')
      }
      
      // Set a playback timeout to ensure we don't hang forever
      const playbackTimeout = setTimeout(() => {
        if (isTtsPlayingRef.current) {
          console.error('TTS playback timeout - forcing cleanup')
          if (audio) {
            audio.pause()
          }
          cleanupTts()
        }
      }, 120000) // 2 minute max playback time
      
      // Clear playback timeout when audio ends normally
      const originalOnEnded = audio.onended
      audio.onended = () => {
        clearTimeout(playbackTimeout)
        originalOnEnded()
      }
      
      const originalOnError = audio.onerror
      audio.onerror = (e) => {
        clearTimeout(playbackTimeout)
        originalOnError(e)
      }
      
      // Apply volume setting
      audio.volume = ttsVolume
      
      setTtsAudio(audio)
      setTtsPlaying(messageIndex)
      setTtsLoading(null)
      
      // Play immediately
      audio.play().catch(err => {
        console.error('Error playing audio:', err)
        clearTimeout(playbackTimeout)
        cleanupTts()
      })
      
    } catch (error) {
      console.error('TTS error:', error)
      setTtsLoading(null)
      isTtsPlayingRef.current = false
    }
  }

  // Save TTS configuration
  const saveTtsConfig = async () => {
    setTtsConfigLoading(true)
    setTtsConfigSaved(false)
    try {
      const headers = { 'Content-Type': 'application/json' }
      const token = getAuthToken()
      if (token) {
        headers['Authorization'] = `Bearer ${token}`
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
  
  // Update volume (stored locally, not synced to server)
  const updateTtsVolume = (volume) => {
    const clampedVolume = Math.max(0, Math.min(1, volume))
    setTtsVolume(clampedVolume)
    localStorage.setItem('ares_tts_volume', String(clampedVolume))
    // Also update currently playing audio if any
    if (ttsAudio) {
      ttsAudio.volume = clampedVolume
    }
  }

  const handleSubmit = async (e) => {
    e.preventDefault()
    if (!input.trim() && !selectedFile) return

    // Stop listening if recording
    const wasInVoiceMode = isVoiceModeRef.current
    if (isListening) {
      stopListening()
    }

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
      const token = getAuthToken()
      if (token) {
        headers['Authorization'] = `Bearer ${token}`
      }

      const response = await fetch('/api/v1/chat', {
        method: 'POST',
        headers,
        body: JSON.stringify(messageData),
      })

      // Use safe JSON parsing to handle HTML error pages gracefully
      const { data, error: parseError } = await safeJsonParse(response)
      
      if (!response.ok) {
        const errorMsg = data?.error || parseError || `Failed to get response (HTTP ${response.status})`
        throw new Error(errorMsg)
      }
      
      if (parseError) {
        throw new Error(parseError)
      }
      
      setIsTyping(false)
      const assistantMessage = {
        type: 'assistant',
        content: data.response || '',
        timestamp: new Date(),
        model: data.model || null,
        provider: data.provider || null,
      }
      
      setMessages(prev => {
        const newMessages = [...prev, assistantMessage]
        // Auto-play TTS if we were in voice mode
        if (wasInVoiceMode && data.response && ttsConfig.api_configured) {
          // Use setTimeout to ensure state is updated, then play TTS
          setTimeout(() => {
            const messageIndex = newMessages.length - 1
            playTTS(data.response, messageIndex)
          }, 300)
        }
        return newMessages
      })
      
      // Only restart listening if voice mode is explicitly enabled
      // Don't auto-restart just because mic was used - only if in voice chat mode
      if (wasInVoiceMode && isVoiceModeRef.current && !isListening) {
        // Restart listening after a short delay to allow response to be processed
        setTimeout(() => {
          if (isVoiceModeRef.current && recognitionRef.current && !isTtsPlayingRef.current) {
            try {
              recognitionRef.current.start()
            } catch (error) {
              // Ignore if already started or other errors
              console.log('Auto-restart listening:', error)
            }
          }
        }, 500)
      }
    } catch (error) {
      console.error('Failed to send message:', error)
      setIsTyping(false)
      setMessages(prev => [...prev, {
        type: 'error',
        content: `Error: ${error.message}`,
        timestamp: new Date(),
      }])
    }

    // Only clear input if not in voice mode (to allow continuation)
    if (!isVoiceModeRef.current) {
      setInput('')
      setSelectedFile(null)
      if (fileInputRef.current) {
        fileInputRef.current.value = ''
      }
      inputRef.current?.focus()
    } else {
      // In voice mode, clear input but keep ready for next speech
      setInput('')
      setSelectedFile(null)
      if (fileInputRef.current) {
        fileInputRef.current.value = ''
      }
      // Update the speech text start ref for next recording
      speechTextStartRef.current = ''
    }
  }

  useEffect(() => {
    // Load available sessions
    const loadSessions = async () => {
      try {
        const headers = {}
        const token = getAuthToken()
        if (token) {
          headers['Authorization'] = `Bearer ${token}`
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
        const token = getAuthToken()
        if (token) {
          headers['Authorization'] = `Bearer ${token}`
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
        const token = getAuthToken()
        if (token) {
          headers['Authorization'] = `Bearer ${token}`
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
      const token = getAuthToken()
      if (token) {
        headers['Authorization'] = `Bearer ${token}`
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
    } else if (!propSessionId) {
      // If no propSessionId, ensure we're using today's daily session
      const dailySessionId = getDailySessionId()
      if (sessionId !== dailySessionId) {
        setSessionId(dailySessionId)
        setIsNewSession(true)
        if (onSessionChange) {
          onSessionChange(dailySessionId)
        }
      }
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [propSessionId]) // Only depend on propSessionId to avoid loops

  useEffect(() => {
    // Load conversation history when sessionId changes
    const loadHistory = async () => {
      try {
        const headers = {}
        const token = getAuthToken()
        if (token) {
          headers['Authorization'] = `Bearer ${token}`
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
      const newSessionId = getDailySessionId()
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
    const newSessionId = getDailySessionId()
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

  // Known Whisper hallucination phrases to filter out
  const HALLUCINATION_PHRASES = [
    'thank you for watching',
    'thanks for watching',
    'please subscribe',
    'like and subscribe',
    'see you next time',
    'bye bye',
    'goodbye',
    'チャンネル登録',
    'お願いします',
    'ご視聴ありがとう',
    'Subtítulos',
    'Subtitles by',
    'Amara.org',
    'this is a conversation with an ai',
    'this is a conversation with an ai assistant',
    'mbc 뉴스',
    '이덕영',
  ]
  
  // Check if text is likely a hallucination
  const isHallucination = (text) => {
    const lowerText = text.toLowerCase()
    
    // Check for known hallucination phrases
    if (HALLUCINATION_PHRASES.some(phrase => lowerText.includes(phrase.toLowerCase()))) {
      return true
    }
    
    // Filter out Japanese, Chinese, Korean, and Russian text (common Whisper hallucinations)
    // Japanese: Hiragana (U+3040-U+309F), Katakana (U+30A0-U+30FF), Kanji (U+4E00-U+9FAF)
    // Chinese: Han characters (U+4E00-U+9FAF) - same range as Kanji
    // Korean: Hangul (U+AC00-U+D7AF)
    // Russian/Cyrillic: Cyrillic (U+0400-U+04FF)
    const asianScriptRegex = /[\u3040-\u309F\u30A0-\u30FF\u4E00-\u9FAF\uAC00-\uD7AF]/
    const cyrillicRegex = /[\u0400-\u04FF]/
    
    // If language is set to English or auto-detect, filter out Russian/Cyrillic
    if ((!speechLanguage || speechLanguage === 'en') && cyrillicRegex.test(text)) {
      return true
    }
    
    if (asianScriptRegex.test(text)) {
      return true
    }
    
    return false
  }

  // Send audio to Whisper API for transcription
  const transcribeAudio = async (audioBlob) => {
    console.log('[STT] transcribeAudio called, blob size:', audioBlob.size, 'type:', audioBlob.type)
    setIsTranscribing(true)
    setSpeechError(null)
    
    try {
      const formData = new FormData()
      // Use the correct extension based on blob type
      const ext = audioBlob.type.includes('webm') ? 'webm' : audioBlob.type.includes('mp4') ? 'mp4' : 'wav'
      formData.append('audio', audioBlob, `recording.${ext}`)
      
      // Only send language if explicitly set (empty = auto-detect)
      if (speechLanguage) {
        formData.append('language', speechLanguage)
      }
      
      // Removed prompt - it was causing Whisper to include "this is a conversation with an AI assistant" 
      // in transcriptions. The prompt parameter can leak into the output, especially with unclear audio.
      
      const headers = {}
      const token = getAuthToken()
      if (token) {
        headers['Authorization'] = `Bearer ${token}`
      }
      
      const response = await fetch('/api/v1/stt', {
        method: 'POST',
        headers,
        body: formData,
      })
      
      if (!response.ok) {
        const error = await response.json()
        throw new Error(error.error || 'Transcription failed')
      }
      
      const data = await response.json()
      let transcribedText = data.text?.trim() || ''
      const detectedLanguage = data.language || ''
      
      // Only process transcription if we're still listening (mic might have been turned off)
      if (!isListeningRef.current && !isVoiceModeRef.current) {
        console.log('[STT] Ignoring transcription - mic is off')
        setIsTranscribing(false)
        speechTextStartRef.current = ''
        return
      }
      
      // Filter out hallucinations
      if (transcribedText && isHallucination(transcribedText)) {
        console.log('[STT] Filtered hallucination:', transcribedText, 'detected language:', detectedLanguage)
        transcribedText = ''
      }
      
      // Additional check: if language is set to English but detected language is Russian, filter it out
      if (transcribedText && (!speechLanguage || speechLanguage === 'en') && detectedLanguage === 'ru') {
        console.log('[STT] Filtered Russian transcription when expecting English:', transcribedText)
        transcribedText = ''
      }
      
      if (transcribedText) {
        // DON'T combine with existing input - just use the new transcription
        // This prevents repeated text issues
        // But only if we're still listening
        if (isListeningRef.current || isVoiceModeRef.current) {
          setInput(transcribedText)
          console.log(`[Whisper] Transcribed (${detectedLanguage}): ${transcribedText}`)
          
          // If in voice mode, auto-submit after transcription
          if (isVoiceModeRef.current && transcribedText.trim()) {
            // Small delay to allow UI to update
            setTimeout(() => {
              // Check again before submitting
              if (isVoiceModeRef.current && isListeningRef.current) {
                const form = inputRef.current?.closest('form')
                if (form) {
                  const submitButton = form.querySelector('button[type="submit"]')
                  if (submitButton && !submitButton.disabled) {
                    console.log('Auto-submitting after Whisper transcription')
                    submitButton.click()
                  }
                }
              }
            }, 100)
          }
        } else {
          console.log('[STT] Ignoring transcription - mic was turned off')
        }
      } else {
        console.log('[STT] No valid speech detected')
        // Don't show error for empty transcriptions in voice mode
        if (!isVoiceModeRef.current) {
          setSpeechError('No speech detected. Try again.')
          setTimeout(() => setSpeechError(null), 3000)
        }
      }
      
    } catch (error) {
      console.error('Whisper transcription error:', error)
      setSpeechError(error.message || 'Transcription failed')
      setTimeout(() => setSpeechError(null), 5000)
    } finally {
      setIsTranscribing(false)
      // Clear the base text reference for next recording
      speechTextStartRef.current = ''
    }
  }

  // Speech recognition handlers
  const startListening = async () => {
    if (isListeningRef.current || isTranscribing) {
      return // Already listening or transcribing
    }
    
    // Don't start if TTS is playing (would create feedback)
    if (isTtsPlayingRef.current) {
      return
    }
    
    // Store current input as base text
    speechTextStartRef.current = input.trim()
    
    // Use Whisper if configured, otherwise fall back to Web Speech API
    console.log('[STT] startListening called, useWhisper:', useWhisper, 'whisperConfigured:', whisperConfigured)
    
    if (useWhisper && whisperConfigured) {
      // Use MediaRecorder for Whisper
      console.log('[STT] Using Whisper/MediaRecorder')
      try {
        const stream = await navigator.mediaDevices.getUserMedia({ audio: true })
        console.log('[STT] Got audio stream')
        
        // Set up silence detection using Web Audio API
        const audioContext = new (window.AudioContext || window.webkitAudioContext)()
        const analyser = audioContext.createAnalyser()
        const microphone = audioContext.createMediaStreamSource(stream)
        microphone.connect(analyser)
        
        analyser.fftSize = 512
        const bufferLength = analyser.frequencyBinCount
        const dataArray = new Uint8Array(bufferLength)
        
        audioContextRef.current = audioContext
        analyserRef.current = analyser
        lastSoundTimeRef.current = Date.now()
        
        // Silence detection parameters
        const SILENCE_THRESHOLD = 15 // Audio level below this is considered silence
        const SILENCE_DURATION = 5000 // Stop after 5 seconds of silence to reduce hallucinations
        const MIN_RECORDING_TIME = 500 // Minimum recording time before silence detection kicks in
        const recordingStartTime = Date.now()
        
        // Flag to prevent multiple stop calls
        let isStopping = false
        
        // Start silence detection interval
        silenceDetectionRef.current = setInterval(() => {
          if (!analyserRef.current || isStopping) return
          
          analyserRef.current.getByteFrequencyData(dataArray)
          
          // Calculate average volume
          let sum = 0
          for (let i = 0; i < bufferLength; i++) {
            sum += dataArray[i]
          }
          const average = sum / bufferLength
          
          // Check if there's sound
          if (average > SILENCE_THRESHOLD) {
            lastSoundTimeRef.current = Date.now()
          }
          
          // Check for silence duration (only after minimum recording time)
          const timeSinceStart = Date.now() - recordingStartTime
          const silenceDuration = Date.now() - lastSoundTimeRef.current
          
          if (timeSinceStart > MIN_RECORDING_TIME && silenceDuration > SILENCE_DURATION) {
            console.log('[STT] Silence detected, auto-stopping recording')
            // Set flag and clear interval BEFORE calling stop
            isStopping = true
            if (silenceDetectionRef.current) {
              clearInterval(silenceDetectionRef.current)
              silenceDetectionRef.current = null
            }
            stopListening()
          }
        }, 100) // Check every 100ms
        
        // Use webm format for best compatibility
        const mimeType = MediaRecorder.isTypeSupported('audio/webm') 
          ? 'audio/webm' 
          : MediaRecorder.isTypeSupported('audio/mp4')
            ? 'audio/mp4'
            : 'audio/wav'
        
        console.log('[STT] Using mimeType:', mimeType)
        
        const mediaRecorder = new MediaRecorder(stream, { mimeType })
        audioChunksRef.current = []
        
        mediaRecorder.ondataavailable = (event) => {
          console.log('[STT] ondataavailable, size:', event.data.size)
          if (event.data.size > 0) {
            audioChunksRef.current.push(event.data)
          }
        }
        
        mediaRecorder.onstop = async () => {
          console.log('[STT] onstop, chunks:', audioChunksRef.current.length)
          
          // Clean up silence detection
          if (silenceDetectionRef.current) {
            clearInterval(silenceDetectionRef.current)
            silenceDetectionRef.current = null
          }
          if (audioContextRef.current) {
            audioContextRef.current.close()
            audioContextRef.current = null
          }
          analyserRef.current = null
          
          // Stop all tracks
          stream.getTracks().forEach(track => track.stop())
          
          if (audioChunksRef.current.length > 0) {
            const audioBlob = new Blob(audioChunksRef.current, { type: mimeType })
            console.log('[STT] Audio blob size:', audioBlob.size)
            
            // Only transcribe if we have a meaningful amount of audio (> 0.5s worth)
            if (audioBlob.size > 5000) {
              await transcribeAudio(audioBlob)
            } else {
              console.log('[STT] Recording too short, ignoring')
              setSpeechError('Recording too short. Please speak longer.')
              setTimeout(() => setSpeechError(null), 3000)
            }
          } else {
            console.log('[STT] No audio chunks recorded')
            setSpeechError('No audio recorded. Please try again.')
            setTimeout(() => setSpeechError(null), 3000)
          }
          
          audioChunksRef.current = []
        }
        
        mediaRecorder.onerror = (event) => {
          console.error('[STT] MediaRecorder error:', event.error)
          
          // Clean up silence detection
          if (silenceDetectionRef.current) {
            clearInterval(silenceDetectionRef.current)
            silenceDetectionRef.current = null
          }
          if (audioContextRef.current) {
            audioContextRef.current.close()
            audioContextRef.current = null
          }
          
          setSpeechError('Recording error. Please try again.')
          setTimeout(() => setSpeechError(null), 3000)
          setIsListening(false)
          stream.getTracks().forEach(track => track.stop())
        }
        
        mediaRecorderRef.current = mediaRecorder
        mediaRecorder.start()
        console.log('[STT] MediaRecorder started with silence detection')
        
        isListeningRef.current = true
        setIsListening(true)
        setSpeechError(null)
        // Don't automatically enable voice mode - only enable it explicitly
        
      } catch (error) {
        console.error('[STT] Failed to start recording:', error)
        if (error.name === 'NotAllowedError') {
          setSpeechError('Microphone permission denied. Please allow microphone access.')
        } else if (error.name === 'NotFoundError') {
          setSpeechError('No microphone found. Please check your microphone.')
        } else {
          setSpeechError(`Failed to start recording: ${error.message}`)
        }
        setTimeout(() => setSpeechError(null), 5000)
      }
    } else if (recognitionRef.current) {
      // Fall back to Web Speech API
      try {
        recognitionRef.current.lang = speechLanguage || 'en-US'
        recognitionRef.current.start()
      } catch (error) {
        console.error('Failed to start recognition:', error)
        if (error.name !== 'InvalidStateError') {
          setSpeechError('Failed to start recording. Please try again.')
          setTimeout(() => setSpeechError(null), 3000)
        }
      }
    } else {
      setSpeechError('Speech recognition not available')
      setTimeout(() => setSpeechError(null), 3000)
    }
  }

  const stopListening = () => {
    console.log('[STT] stopListening called, isListeningRef:', isListeningRef.current)
    if (!isListeningRef.current) {
      return
    }
    
    // Set ref immediately to prevent re-entry
    isListeningRef.current = false
    
    // Clean up silence detection first
    if (silenceDetectionRef.current) {
      clearInterval(silenceDetectionRef.current)
      silenceDetectionRef.current = null
    }
    
    // Stop MediaRecorder (Whisper)
    if (mediaRecorderRef.current && mediaRecorderRef.current.state !== 'inactive') {
      console.log('[STT] Stopping MediaRecorder, state:', mediaRecorderRef.current.state)
      try {
        mediaRecorderRef.current.stop()
      } catch (error) {
        console.error('[STT] Failed to stop MediaRecorder:', error)
      }
    }
    
    // Stop Web Speech API (fallback)
    if (recognitionRef.current) {
      try {
        recognitionRef.current.stop()
      } catch (error) {
        console.error('Failed to stop recognition:', error)
      }
    }
    
    setIsListening(false)
    
    // Clear silence timeout
    if (silenceTimeoutRef.current) {
      clearTimeout(silenceTimeoutRef.current)
      silenceTimeoutRef.current = null
    }
  }

  // Track last click time for double-click detection
  const lastClickTimeRef = useRef(0)
  
  const toggleListening = (e) => {
    // Check for double-click to toggle voice mode
    const now = Date.now()
    const timeSinceLastClick = now - lastClickTimeRef.current
    lastClickTimeRef.current = now
    
    if (timeSinceLastClick < 300 && !isListening) {
      // Double-click detected - toggle voice mode
      const newVoiceMode = !isVoiceModeRef.current
      isVoiceModeRef.current = newVoiceMode
      setIsVoiceMode(newVoiceMode)
      console.log('Voice mode toggled:', newVoiceMode)
      return
    }
    
    if (isListening) {
      stopListening()
      // Don't clear voice mode when manually stopped - let user control it separately
      // Voice mode persists until explicitly toggled off
    } else {
      startListening()
      // When starting to listen, enable voice mode if it's already enabled
      // This ensures voice mode state is maintained
      if (isVoiceModeRef.current) {
        setIsVoiceMode(true)
      }
    }
  }
  
  // Sync voice mode state with ref when it changes
  useEffect(() => {
    // This effect ensures the UI state matches the ref
    // The ref is the source of truth, but we update state for UI rendering
  }, [])

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
      const token = getAuthToken()
      if (token) {
        headers['Authorization'] = `Bearer ${token}`
      }

      const response = await fetch('/api/v1/chat', {
        method: 'POST',
        headers,
        body: JSON.stringify({
          message: messageContent,
          session_id: sessionId,
        }),
      })

      // Use safe JSON parsing to handle HTML error pages gracefully
      const { data, error: parseError } = await safeJsonParse(response)
      
      if (!response.ok) {
        throw new Error(data?.error || parseError || 'Failed to analyze codebase')
      }
      
      if (parseError) {
        throw new Error(parseError)
      }
      
      setIsTyping(false)
      setMessages(prev => [...prev, {
        type: 'assistant',
        content: data?.response || '',
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

  const handleIndexCodebase = async () => {
    try {
      setIsTyping(true)
      setMessages(prev => [...prev, {
        type: 'system',
        content: 'Indexing codebase... This may take a moment.',
        timestamp: new Date(),
      }])

      const headers = {
        'Content-Type': 'application/json',
      }
      const token = getAuthToken()
      if (token) {
        headers['Authorization'] = `Bearer ${token}`
      }

      const response = await fetch('/api/v1/code/index', {
        method: 'POST',
        headers,
      })

      // Use safe JSON parsing to handle HTML error pages gracefully
      const { data, error: parseError } = await safeJsonParse(response)
      
      if (!response.ok) {
        throw new Error(data?.error || parseError || 'Failed to index codebase')
      }
      
      if (parseError) {
        throw new Error(parseError)
      }
      
      setIsTyping(false)
      setMessages(prev => [...prev, {
        type: 'system',
        content: `Codebase indexed successfully! ${data?.indexed || 0} files indexed (${data?.created || 0} new, ${data?.updated || 0} updated). The AI now has access to all code files.`,
        timestamp: new Date(),
      }])
    } catch (error) {
      console.error('Failed to index codebase:', error)
      setIsTyping(false)
      setMessages(prev => [...prev, {
        type: 'error',
        content: `Error indexing codebase: ${error.message}`,
        timestamp: new Date(),
      }])
    }
  }

  return (
    <div className="chat-panel">
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
            {availableSessions.map((sid) => {
              // Format session ID for display
              let displayText = sid
              if (sid.startsWith('daily_')) {
                displayText = sid.replace('daily_', '') // Show as YYYY-MM-DD
              } else if (sid.startsWith('session_')) {
                displayText = sid.replace('session_', '').substring(0, 20) + '...'
              }
              return (
                <option key={sid} value={sid}>
                  {displayText}
                </option>
              )
            })}
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
          {isSpeechSupported && (
            <select
              value={speechLanguage}
              onChange={(e) => setSpeechLanguage(e.target.value)}
              className="language-selector"
              title={useWhisper && whisperConfigured ? "Speech language (Whisper - auto-detect if empty)" : "Speech recognition language"}
            >
              {useWhisper && whisperConfigured && (
                <option value="">🌍 Auto-detect</option>
              )}
              <option value="en">🇺🇸 English</option>
              <option value="es">🇪🇸 Español</option>
              <option value="fr">🇫🇷 Français</option>
              <option value="de">🇩🇪 Deutsch</option>
              <option value="pt">🇧🇷 Português</option>
              <option value="it">🇮🇹 Italiano</option>
              <option value="zh">🇨🇳 中文</option>
              <option value="ja">🇯🇵 日本語</option>
              <option value="ko">🇰🇷 한국어</option>
            </select>
          )}
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
          
          <div className="tts-setting volume-setting">
            <label>
              Volume: {Math.round(ttsVolume * 100)}%
              {ttsVolume === 0 && ' 🔇'}
              {ttsVolume > 0 && ttsVolume <= 0.3 && ' 🔈'}
              {ttsVolume > 0.3 && ttsVolume <= 0.7 && ' 🔉'}
              {ttsVolume > 0.7 && ' 🔊'}
            </label>
            <input
              type="range"
              min="0"
              max="1"
              step="0.05"
              value={ttsVolume}
              onChange={(e) => updateTtsVolume(parseFloat(e.target.value))}
              className="volume-slider"
            />
            <span className="tts-setting-hint">Adjust playback volume (saved locally)</span>
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
          {sessionId.startsWith('daily_') 
            ? `Today's conversation: ${sessionId.replace('daily_', '')}`
            : `Starting new conversation session: ${sessionId.substring(0, 30)}...`
          }
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
          {isSpeechSupported && (
            <div style={{ position: 'relative' }}>
              {speechError && (
                <div className="speech-error-tooltip">{speechError}</div>
              )}
              <button
                type="button"
                onClick={toggleListening}
                className={`mic-button ${isListening ? 'listening' : ''} ${isTranscribing ? 'transcribing' : ''} ${isVoiceMode ? 'voice-mode' : ''}`}
                title={isTranscribing ? 'Processing speech...' : isListening ? 'Stop recording (double-click to toggle voice mode)' : `Start voice input${useWhisper && whisperConfigured ? ' (Whisper)' : ''}${isVoiceMode ? ' - Voice mode ON (double-click to toggle)' : ' (double-click to enable voice mode)'}`}
                disabled={isTyping || isTranscribing}
              >
                {isTranscribing ? '⏳' : isListening ? '🎤' : isVoiceMode ? '🎙️✨' : '🎙️'}
              </button>
            </div>
          )}
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
            type="button"
            onClick={handleIndexCodebase}
            className="code-index-button"
            title="Index all code files for AI access"
          >
            📚
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

