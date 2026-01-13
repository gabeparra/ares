import React, { useState, useEffect } from 'react'

function PowerPetDoorControl() {
  const [enabled, setEnabled] = useState(false)
  const [loading, setLoading] = useState(false)
  const [doorState, setDoorState] = useState(null)
  const [switches, setSwitches] = useState({})
  const [sensors, setSensors] = useState({})
  const [error, setError] = useState(null)

  useEffect(() => {
    fetchStatus()
    const interval = setInterval(() => {
      if (enabled) {
        fetchDoorState()
        fetchAllStates()
      }
    }, 5000) // Refresh every 5 seconds

    return () => clearInterval(interval)
  }, [enabled])

  const fetchStatus = async () => {
    try {
      const response = await fetch('/api/powerpetdoor/status')
      if (response.ok) {
        const data = await response.json()
        setEnabled(data.enabled)
        if (data.enabled) {
          fetchDoorState()
          fetchAllStates()
        }
      }
    } catch (err) {
      console.error('Failed to fetch Power Pet Door status:', err)
      setEnabled(false)
    }
  }

  const fetchDoorState = async () => {
    try {
      const response = await fetch('/api/powerpetdoor/door')
      if (response.ok) {
        const data = await response.json()
        setDoorState(data)
      } else if (response.status === 503) {
        setEnabled(false)
      }
    } catch (err) {
      console.error('Failed to fetch door state:', err)
      setError('Failed to connect to Power Pet Door')
    }
  }

  const fetchAllStates = async () => {
    try {
      const response = await fetch('/api/powerpetdoor/all')
      if (response.ok) {
        const data = await response.json()
        const switchStates = {}
        const sensorValues = {}
        
        Object.entries(data.states || {}).forEach(([key, state]) => {
          const [domain, name] = key.split('.')
          if (domain === 'switch') {
            switchStates[name] = state
          } else if (domain === 'sensor') {
            sensorValues[name] = state
          }
        })
        
        setSwitches(switchStates)
        setSensors(sensorValues)
      }
    } catch (err) {
      console.error('Failed to fetch all states:', err)
    }
  }

  const handleDoorAction = async (action) => {
    setLoading(true)
    setError(null)
    try {
      const response = await fetch(`/api/powerpetdoor/door/${action}`, {
        method: 'POST',
      })
      if (response.ok) {
        await fetchDoorState()
      } else {
        const data = await response.json()
        setError(data.error || 'Failed to control door')
      }
    } catch (err) {
      setError('Failed to control door')
    } finally {
      setLoading(false)
    }
  }

  const handleSwitchToggle = async (switchName) => {
    setLoading(true)
    setError(null)
    try {
      const response = await fetch(`/api/powerpetdoor/switch/${switchName}/toggle`, {
        method: 'POST',
      })
      if (response.ok) {
        await fetchAllStates()
      } else {
        const data = await response.json()
        setError(data.error || 'Failed to toggle switch')
      }
    } catch (err) {
      setError('Failed to toggle switch')
    } finally {
      setLoading(false)
    }
  }

  const getDoorStatus = () => {
    if (!doorState) return 'Unknown'
    const state = doorState.state
    const position = doorState.attributes?.current_position ?? 0
    
    if (state === 'open' || position === 100) return 'Open'
    if (state === 'closed' || position === 0) return 'Closed'
    if (state === 'opening') return 'Opening'
    if (state === 'closing') return 'Closing'
    return state
  }

  const getDoorStatusClass = () => {
    if (!doorState) return ''
    const state = doorState.state
    if (state === 'open') return 'open'
    if (state === 'closed') return 'closed'
    if (state === 'opening' || state === 'closing') return 'moving'
    return ''
  }

  if (!enabled) {
    return (
      <div className="power-pet-door-control disabled">
        <div className="door-status">
          <span className="status-indicator"></span>
          <span className="status-text">Power Pet Door Not Configured</span>
        </div>
        <div className="door-info">
          <p>Configure HOME_ASSISTANT_URL and HOME_ASSISTANT_TOKEN in your .env file</p>
        </div>
      </div>
    )
  }

  return (
    <div className={`power-pet-door-control ${getDoorStatusClass()}`}>
      <div className="door-header">
        <h3>Power Pet Door</h3>
        {error && <div className="error-message">{error}</div>}
      </div>

      <div className="door-control-section">
        <div className="door-status-display">
          <span className="status-indicator"></span>
          <span className="status-text">Door: {getDoorStatus()}</span>
          {doorState?.attributes?.current_position !== undefined && (
            <span className="door-position">
              {doorState.attributes.current_position}%
            </span>
          )}
        </div>

        <div className="door-buttons">
          <button
            onClick={() => handleDoorAction('open')}
            disabled={loading}
            className="door-btn open-btn"
            title="Open door"
          >
            Open
          </button>
          <button
            onClick={() => handleDoorAction('close')}
            disabled={loading}
            className="door-btn close-btn"
            title="Close door"
          >
            Close
          </button>
          <button
            onClick={() => handleDoorAction('stop')}
            disabled={loading}
            className="door-btn stop-btn"
            title="Stop door"
          >
            Stop
          </button>
          <button
            onClick={() => handleDoorAction('cycle')}
            disabled={loading}
            className="door-btn cycle-btn"
            title="Cycle door (open/close)"
          >
            Cycle
          </button>
        </div>
      </div>

      <div className="switches-section">
        <h4>Controls</h4>
        <div className="switches-grid">
          {Object.entries(switches).map(([name, state]) => {
            const isOn = state?.state === 'on'
            const friendlyName = name.replace(/_/g, ' ').replace(/\b\w/g, l => l.toUpperCase())
            return (
              <div key={name} className="switch-item">
                <label className="switch-label">
                  <input
                    type="checkbox"
                    checked={isOn}
                    onChange={() => handleSwitchToggle(name)}
                    disabled={loading}
                  />
                  <span className="switch-name">{friendlyName}</span>
                </label>
              </div>
            )
          })}
        </div>
      </div>

      {Object.keys(sensors).length > 0 && (
        <div className="sensors-section">
          <h4>Sensors</h4>
          <div className="sensors-list">
            {Object.entries(sensors).map(([name, sensor]) => {
              const friendlyName = name.replace(/_/g, ' ').replace(/\b\w/g, l => l.toUpperCase())
              return (
                <div key={name} className="sensor-item">
                  <span className="sensor-name">{friendlyName}:</span>
                  <span className="sensor-value">{sensor?.state} {sensor?.attributes?.unit_of_measurement || ''}</span>
                </div>
              )
            })}
          </div>
        </div>
      )}
    </div>
  )
}

export default PowerPetDoorControl

