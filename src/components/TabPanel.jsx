import React from 'react'
import '../styles/TabPanel.css'

function TabPanel({ children, active, id }) {
  if (!active) {
    return null
  }

  return (
    <div className="tab-panel" data-tab-id={id}>
      {children}
    </div>
  )
}

export default TabPanel

