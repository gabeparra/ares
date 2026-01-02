import React from 'react'
import '../styles/TabPanel.css'

function TabPanel({ children, active, id }) {
  return (
    <div className={`tab-panel ${active ? 'active' : 'hidden'}`} data-tab-id={id}>
      {children}
    </div>
  )
}

export default TabPanel

