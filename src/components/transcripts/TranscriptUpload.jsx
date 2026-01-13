import React, { useState, useRef, useEffect } from 'react'
import ReactMarkdown from 'react-markdown'
import { getAuthToken } from '../../services/auth'

// Summary-focused system prompt for transcript analysis
const TRANSCRIPT_SUMMARY_PROMPT = `You are a meeting transcript analysis assistant. Your role is to provide clear, concise summaries of meeting transcripts.

When analyzing a transcript:
- Provide a structured summary with key points, decisions, and action items
- Focus on facts and important information
- Be concise and avoid conversational language
- Organize information logically (e.g., Participants, Agenda, Key Discussion Points, Decisions, Action Items)
- Do not engage in back-and-forth conversation - just provide the summary

Your responses should be direct and informative summaries, not conversational exchanges.`

function TranscriptUpload({ onSummaryGenerated }) {
  const [file, setFile] = useState(null)
  const [isProcessing, setIsProcessing] = useState(false)
  const [summary, setSummary] = useState(null)
  const [error, setError] = useState(null)
  const [transcriptContent, setTranscriptContent] = useState(null) // Store the actual transcript content
  
  // Chat section state
  const [chatMessages, setChatMessages] = useState([])
  const [chatInput, setChatInput] = useState('')
  const [isChatTyping, setIsChatTyping] = useState(false)
  const [chatSessionId] = useState(() => `transcript_chat_${Date.now()}`)
  const chatMessagesEndRef = useRef(null)

  const handleFileSelect = (e) => {
    const selectedFile = e.target.files[0]
    if (selectedFile) {
      setFile(selectedFile)
      setError(null)
      setSummary(null)
      setTranscriptContent(null) // Clear previous transcript content
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

  // Scroll chat to bottom when new messages arrive
  useEffect(() => {
    chatMessagesEndRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [chatMessages])

  const handleUpload = async () => {
    if (!file) return

    setIsProcessing(true)
    setError(null)
    setSummary(null)

    try {
      const content = await readFileContent(file)
      
      // Store the transcript content for chat context
      setTranscriptContent(content)
      
      const headers = {
        'Content-Type': 'application/json',
      }
      const token = getAuthToken()
      if (token) {
        headers['Authorization'] = `Bearer ${token}`
      }

      // Send transcript for summarization with summary-focused prompt
      const response = await fetch('/api/v1/chat', {
        method: 'POST',
        headers,
        body: JSON.stringify({
          message: `Please provide a comprehensive summary of this meeting transcript:\n\n${content}`,
          session_id: `transcript_${Date.now()}`,
          system_prompt_override: TRANSCRIPT_SUMMARY_PROMPT,
        }),
      })

      if (!response.ok) {
        const errorData = await response.json()
        throw new Error(errorData.error || 'Failed to generate summary')
      }

      const data = await response.json()
      setSummary(data.response)
      
      // Add a welcome message to chat when transcript is loaded
      setChatMessages([{
        type: 'assistant',
        content: `I've loaded the transcript from "${file.name}". You can now ask me questions about the meeting, request specific information, or discuss the content.`,
        timestamp: new Date(),
      }])
      
      if (onSummaryGenerated) {
        onSummaryGenerated(data.response, file.name)
      }
    } catch (err) {
      console.error('Failed to process transcript:', err)
      setError(err.message)
    } finally {
      setIsProcessing(false)
    }
  }

  const handleChatSubmit = async (e) => {
    e.preventDefault()
    if (!chatInput.trim()) return

    const userMessage = {
      type: 'user',
      content: chatInput,
      timestamp: new Date(),
    }

    setChatMessages(prev => [...prev, userMessage])
    setIsChatTyping(true)
    setChatInput('')

    try {
      const headers = {
        'Content-Type': 'application/json',
      }
      const token = getAuthToken()
      if (token) {
        headers['Authorization'] = `Bearer ${token}`
      }

      // Create system prompt that includes transcript content if available
      let systemPromptOverride = null
      if (transcriptContent) {
        systemPromptOverride = `You are a helpful assistant that can answer questions about meeting transcripts. 

Below is the full meeting transcript that the user is asking about. Use this transcript to answer their questions accurately and provide specific details when requested.

MEETING TRANSCRIPT:
${transcriptContent}

When answering questions:
- Reference specific parts of the transcript when relevant
- Provide accurate information based on what was discussed
- If asked about something not in the transcript, say so clearly
- Be helpful and conversational while staying accurate to the transcript content`
      }

      const response = await fetch('/api/v1/chat', {
        method: 'POST',
        headers,
        body: JSON.stringify({
          message: chatInput,
          session_id: chatSessionId,
          system_prompt_override: systemPromptOverride,
        }),
      })

      if (!response.ok) {
        const errorData = await response.json()
        throw new Error(errorData.error || 'Failed to get response')
      }

      const data = await response.json()
      setIsChatTyping(false)
      
      const assistantMessage = {
        type: 'assistant',
        content: data.response || '',
        timestamp: new Date(),
      }
      
      setChatMessages(prev => [...prev, assistantMessage])
    } catch (err) {
      console.error('Failed to send chat message:', err)
      setIsChatTyping(false)
      setChatMessages(prev => [...prev, {
        type: 'error',
        content: `Error: ${err.message}`,
        timestamp: new Date(),
      }])
    }
  }

  const handleClear = () => {
    setFile(null)
    setSummary(null)
    setError(null)
    setTranscriptContent(null)
    setChatMessages([]) // Clear chat messages when transcript is cleared
  }

  return (
    <div className="panel transcript-upload-panel">
      <h2>📄 Meeting Transcripts</h2>
      
      <div className="transcript-container">
        {/* Upload Section */}
        <div className="transcript-section upload-section">
          <h3>📤 Upload & Summary</h3>
          
          <div className="file-input-wrapper">
            <input
              type="file"
              id="transcript-file"
              accept=".txt,.md,.doc,.docx"
              onChange={handleFileSelect}
              className="file-input"
            />
            <label htmlFor="transcript-file" className="file-label">
              {file ? file.name : 'Select Transcript File'}
            </label>
          </div>

          {file && (
            <div className="file-actions">
              <button
                onClick={handleUpload}
                disabled={isProcessing}
                className="upload-button"
              >
                {isProcessing ? 'Processing...' : 'Generate Summary'}
              </button>
              <button
                onClick={handleClear}
                disabled={isProcessing}
                className="clear-button"
              >
                Clear
              </button>
            </div>
          )}

          {error && (
            <div className="error-message">
              ⚠️ {error}
            </div>
          )}

          {isProcessing && (
            <div className="processing-indicator">
              <div className="spinner"></div>
              <span>Analyzing transcript...</span>
            </div>
          )}

          {summary && (
            <div className="summary-section">
              <h4>Summary</h4>
              <div className="summary-content">
                {summary}
              </div>
            </div>
          )}
        </div>

        {/* Chat Section */}
        <div className="transcript-section chat-section">
          <h3>💬 Chat with AI</h3>
          
          <div className="chat-messages">
            {chatMessages.length === 0 && (
              <div className="chat-empty">
                <p>
                  {transcriptContent 
                    ? 'Transcript loaded! Ask me questions about the meeting, request specific information, or discuss the content.'
                    : 'Upload a transcript file to start chatting about it. Once uploaded, I\'ll be able to answer questions about the meeting content.'}
                </p>
              </div>
            )}
            
            {chatMessages.map((msg, idx) => (
              <div key={idx} className={`chat-message ${msg.type}`}>
                <div className="chat-message-content">
                  {msg.type === 'user' ? (
                    <div className="user-message">{msg.content}</div>
                  ) : msg.type === 'error' ? (
                    <div className="error-message">⚠️ {msg.content}</div>
                  ) : (
                    <div className="assistant-message">
                      <ReactMarkdown>{msg.content}</ReactMarkdown>
                    </div>
                  )}
                </div>
              </div>
            ))}
            
            {isChatTyping && (
              <div className="chat-message assistant">
                <div className="chat-message-content">
                  <div className="typing-indicator">
                    <span></span>
                    <span></span>
                    <span></span>
                  </div>
                </div>
              </div>
            )}
            
            <div ref={chatMessagesEndRef} />
          </div>

          <form onSubmit={handleChatSubmit} className="chat-input-form">
            <input
              type="text"
              value={chatInput}
              onChange={(e) => setChatInput(e.target.value)}
              placeholder="Ask about transcripts, request summaries, or discuss meetings..."
              className="chat-input"
              disabled={isChatTyping}
            />
            <button
              type="submit"
              disabled={!chatInput.trim() || isChatTyping}
              className="chat-send-button"
            >
              Send
            </button>
          </form>
        </div>
      </div>
    </div>
  )
}

export default TranscriptUpload

