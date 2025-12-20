import React, { useState } from 'react'
import './TranscriptUpload.css'

function TranscriptUpload({ onSummaryGenerated }) {
  const [file, setFile] = useState(null)
  const [isProcessing, setIsProcessing] = useState(false)
  const [summary, setSummary] = useState(null)
  const [error, setError] = useState(null)

  const handleFileSelect = (e) => {
    const selectedFile = e.target.files[0]
    if (selectedFile) {
      setFile(selectedFile)
      setError(null)
      setSummary(null)
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

  const handleUpload = async () => {
    if (!file) return

    setIsProcessing(true)
    setError(null)
    setSummary(null)

    try {
      const content = await readFileContent(file)
      
      const headers = {
        'Content-Type': 'application/json',
      }
      if (window.authToken) {
        headers['Authorization'] = `Bearer ${window.authToken}`
      }

      // Send transcript for summarization
      const response = await fetch('/api/v1/chat', {
        method: 'POST',
        headers,
        body: JSON.stringify({
          message: `Please provide a comprehensive summary of this meeting transcript:\n\n${content}`,
          session_id: `transcript_${Date.now()}`,
        }),
      })

      if (!response.ok) {
        const errorData = await response.json()
        throw new Error(errorData.error || 'Failed to generate summary')
      }

      const data = await response.json()
      setSummary(data.response)
      
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

  const handleClear = () => {
    setFile(null)
    setSummary(null)
    setError(null)
  }

  return (
    <div className="panel transcript-upload-panel">
      <h2>📄 Meeting Transcript Summary</h2>
      
      <div className="upload-section">
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
      </div>

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
          <h3>Summary</h3>
          <div className="summary-content">
            {summary}
          </div>
        </div>
      )}
    </div>
  )
}

export default TranscriptUpload

