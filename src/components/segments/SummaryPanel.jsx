import React from 'react'

function SummaryPanel({ summary }) {
  return (
    <div className="panel summary-panel">
      <h2>Ares Analysis</h2>
      <div className="summary-content">
        {summary ? (
          <div className="summary-text">{summary.split('\n').map((line, idx) => (
            <React.Fragment key={idx}>
              {line}
              <br />
            </React.Fragment>
          ))}</div>
        ) : (
          <div className="empty-state">No analysis available yet...</div>
        )}
      </div>
    </div>
  )
}

export default SummaryPanel

