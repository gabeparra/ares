import React from 'react'

function TabPanel({ children, active, id }) {
  return (
    <div className={`flex flex-col flex-1 min-h-0 h-full w-full overflow-hidden box-border p-0 ${active ? 'flex' : 'hidden'}`} data-tab-id={id}>
      {children}
    </div>
  )
}

export default TabPanel

