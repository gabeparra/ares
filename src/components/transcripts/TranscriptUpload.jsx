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
    <div className="panel flex flex-col gap-5">
      <h2 className="m-0 mb-5 text-xl font-semibold bg-gradient-to-r from-white to-red-accent bg-clip-text text-transparent flex-shrink-0">
        📄 Meeting Transcripts
      </h2>
      
      <div className="flex flex-col gap-5 flex-1 min-h-0 overflow-hidden">
        {/* Upload Section */}
        <div className="flex flex-col bg-white-opacity-3 border border-white-opacity-8 rounded-2xl p-5 flex-shrink-0">
          <h3 className="m-0 mb-4 text-lg font-semibold text-white-opacity-92 flex-shrink-0">
            📤 Upload & Summary
          </h3>
          
          <div className="relative mb-4">
            <input
              type="file"
              id="transcript-file"
              accept=".txt,.md,.doc,.docx"
              onChange={handleFileSelect}
              className="absolute w-0 h-0 opacity-0 overflow-hidden"
            />
            <label
              htmlFor="transcript-file"
              className="block px-4 py-3 bg-white-opacity-6 border border-white-opacity-12 rounded-lg text-white-opacity-80 text-sm cursor-pointer transition-all duration-250 text-center hover:bg-white-opacity-10 hover:border-white-opacity-20"
            >
              {file ? file.name : 'Select Transcript File'}
            </label>
          </div>

          {file && (
            <div className="flex gap-2.5 mb-4">
              <button
                onClick={handleUpload}
                disabled={isProcessing}
                className="flex-1 px-5 py-3 bg-gradient-to-br from-red-bg-6 via-red-bg-5 to-red-bg-6 border-none rounded-lg text-white text-sm font-medium cursor-pointer transition-all duration-250 hover:from-red-bg-5 hover:to-red-bg-6 hover:-translate-y-0.5 hover:shadow-button-hover disabled:opacity-50 disabled:cursor-not-allowed disabled:hover:translate-y-0"
              >
                {isProcessing ? 'Processing...' : 'Generate Summary'}
              </button>
              <button
                onClick={handleClear}
                disabled={isProcessing}
                className="flex-1 px-5 py-3 bg-white-opacity-6 border border-white-opacity-12 rounded-lg text-white-opacity-80 text-sm font-medium cursor-pointer transition-all duration-250 hover:bg-white-opacity-10 hover:border-white-opacity-20 disabled:opacity-50 disabled:cursor-not-allowed"
              >
                Clear
              </button>
            </div>
          )}

          {error && (
            <div className="px-4 py-3 bg-red-500/15 border border-red-500/30 rounded-lg text-red-300 text-sm mb-4">
              ⚠️ {error}
            </div>
          )}

          {isProcessing && (
            <div className="flex items-center gap-3 px-3 py-3 bg-white-opacity-3 rounded-lg text-white-opacity-70 text-sm mb-4">
              <div className="w-5 h-5 border-2 border-white-opacity-20 border-t-red-500/80 rounded-full animate-spin"></div>
              <span>Analyzing transcript...</span>
            </div>
          )}

          {summary && (
            <div className="mt-4 pt-4 border-t border-white-opacity-10">
              <h4 className="m-0 mb-3 text-base font-semibold text-white-opacity-92">Summary</h4>
              <div className="p-4 bg-black/20 rounded-lg text-white-opacity-85 leading-relaxed whitespace-pre-wrap break-words max-h-[400px] overflow-y-auto">
                {summary}
              </div>
            </div>
          )}
        </div>

        {/* Chat Section */}
        <div className="flex flex-col bg-white-opacity-3 border border-white-opacity-8 rounded-2xl p-5 flex-1 min-h-0 overflow-hidden">
          <h3 className="m-0 mb-4 text-lg font-semibold text-white-opacity-92 flex-shrink-0">
            💬 Chat with AI
          </h3>
          
          <div className="flex-1 min-h-0 overflow-y-auto overflow-x-hidden px-3 py-3 mb-4 pr-1">
            {chatMessages.length === 0 && (
              <div className="empty-state">
                <p className="m-0">
                  {transcriptContent 
                    ? 'Transcript loaded! Ask me questions about the meeting, request specific information, or discuss the content.'
                    : 'Upload a transcript file to start chatting about it. Once uploaded, I\'ll be able to answer questions about the meeting content.'}
                </p>
              </div>
            )}
            
            {chatMessages.map((msg, idx) => (
              <div
                key={idx}
                className={`mb-4 px-5 py-4 rounded-2xl animate-slide-in-up transition-all duration-200 ${
                  msg.type === 'user'
                    ? 'bg-gradient-to-br from-red-bg-4 to-red-bg-3 border border-red-border-2 ml-6'
                    : msg.type === 'error'
                    ? 'bg-red-500/15 border border-red-500/30'
                    : 'bg-white-opacity-4 border border-white-opacity-10 mr-6'
                }`}
              >
                <div className="leading-relaxed text-white-opacity-90 break-words">
                  {msg.type === 'user' ? (
                    <div>{msg.content}</div>
                  ) : msg.type === 'error' ? (
                    <div className="text-red-300">⚠️ {msg.content}</div>
                  ) : (
                    <div>
                      <ReactMarkdown>{msg.content}</ReactMarkdown>
                    </div>
                  )}
                </div>
              </div>
            ))}
            
            {isChatTyping && (
              <div className="mb-4 px-5 py-4 rounded-2xl bg-white-opacity-4 border border-white-opacity-10 mr-6 animate-slide-in-up">
                <div className="flex gap-1.5 py-2">
                  <span className="w-2 h-2 bg-red-500/60 rounded-full animate-typing"></span>
                  <span className="w-2 h-2 bg-red-500/60 rounded-full animate-typing" style={{ animationDelay: '0.2s' }}></span>
                  <span className="w-2 h-2 bg-red-500/60 rounded-full animate-typing" style={{ animationDelay: '0.4s' }}></span>
                </div>
              </div>
            )}
            
            <div ref={chatMessagesEndRef} />
          </div>

          <form onSubmit={handleChatSubmit} className="flex gap-2.5 flex-shrink-0 pt-4 border-t border-white-opacity-10">
            <input
              type="text"
              value={chatInput}
              onChange={(e) => setChatInput(e.target.value)}
              placeholder="Ask about transcripts, request summaries, or discuss meetings..."
              className="flex-1 min-w-0 px-4 py-3.5 bg-white-opacity-6 border border-white-opacity-12 rounded-2xl text-white text-base outline-none transition-all duration-250 placeholder:text-white-opacity-40 focus:border-red-border-4 focus:bg-white-opacity-8 focus:shadow-[0_0_0_4px_rgba(255,0,0,0.1)] disabled:opacity-50 disabled:cursor-not-allowed"
              disabled={isChatTyping}
            />
            <button
              type="submit"
              disabled={!chatInput.trim() || isChatTyping}
              className="px-7 py-3.5 bg-gradient-to-br from-red-bg-6 via-red-bg-5 to-red-bg-6 border-none rounded-2xl text-white font-semibold text-sm cursor-pointer transition-all duration-250 flex-shrink-0 hover:from-red-bg-5 hover:to-red-bg-6 hover:-translate-y-0.5 hover:shadow-button-hover disabled:opacity-40 disabled:cursor-not-allowed disabled:hover:translate-y-0"
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

