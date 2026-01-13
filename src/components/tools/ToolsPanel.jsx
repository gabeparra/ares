import React, { useState, useCallback } from 'react'

const ALGORITHMS = [
  { id: 'random', label: 'Random', description: 'Cryptographically secure random password' },
  { id: 'pronounceable', label: 'Pronounceable', description: 'Easy to remember, readable password' },
  { id: 'pattern', label: 'Pattern-Based', description: 'Alternating character types' },
  { id: 'xkcd', label: 'XKCD-Style', description: 'Word-based passphrase' },
]

const CHARACTER_SETS = {
  uppercase: 'ABCDEFGHIJKLMNOPQRSTUVWXYZ',
  lowercase: 'abcdefghijklmnopqrstuvwxyz',
  numbers: '0123456789',
  symbols: '!@#$%^&*()_+-=[]{}|;:,.<>?',
  special: '~`"\'\\/',
}

const COMMON_WORDS = [
  'apple', 'banana', 'cherry', 'dragon', 'eagle', 'forest', 'galaxy', 'hammer',
  'island', 'jigsaw', 'knight', 'lighthouse', 'mountain', 'nebula', 'ocean', 'planet',
  'quantum', 'rainbow', 'sunset', 'thunder', 'universe', 'volcano', 'wizard', 'xylophone',
  'yacht', 'zeppelin', 'alpha', 'beta', 'gamma', 'delta', 'echo', 'foxtrot'
]

function ToolsPanel() {
  const [activeTool, setActiveTool] = useState('password-generator')
  const [password, setPassword] = useState('')
  const [length, setLength] = useState(16)
  const [algorithm, setAlgorithm] = useState('random')
  const [characterTypes, setCharacterTypes] = useState({
    uppercase: true,
    lowercase: true,
    numbers: true,
    symbols: false,
    special: false,
  })
  const [copied, setCopied] = useState(false)

  // Generate password based on selected algorithm
  const generatePassword = useCallback(() => {
    let generated = ''

    // Get available character set based on checkboxes
    let availableChars = ''
    if (characterTypes.uppercase) availableChars += CHARACTER_SETS.uppercase
    if (characterTypes.lowercase) availableChars += CHARACTER_SETS.lowercase
    if (characterTypes.numbers) availableChars += CHARACTER_SETS.numbers
    if (characterTypes.symbols) availableChars += CHARACTER_SETS.symbols
    if (characterTypes.special) availableChars += CHARACTER_SETS.special

    if (availableChars.length === 0) {
      setPassword('Please select at least one character type')
      return
    }

    switch (algorithm) {
      case 'random':
        // Cryptographically secure random
        const array = new Uint32Array(length)
        crypto.getRandomValues(array)
        generated = Array.from(array)
          .map((val) => availableChars[val % availableChars.length])
          .join('')
        break

      case 'pronounceable':
        // Generate pronounceable password (consonant-vowel pattern)
        const vowels = 'aeiou'
        const consonants = 'bcdfghjklmnpqrstvwxyz'
        for (let i = 0; i < length; i++) {
          if (i % 2 === 0) {
            generated += consonants[Math.floor(Math.random() * consonants.length)]
          } else {
            generated += vowels[Math.floor(Math.random() * vowels.length)]
          }
        }
        // Ensure at least one character from each selected type
        if (characterTypes.uppercase && !/[A-Z]/.test(generated)) {
          const pos = Math.floor(Math.random() * generated.length)
          generated = generated.slice(0, pos) + 
            CHARACTER_SETS.uppercase[Math.floor(Math.random() * CHARACTER_SETS.uppercase.length)] + 
            generated.slice(pos + 1)
        }
        if (characterTypes.numbers && !/[0-9]/.test(generated)) {
          const pos = Math.floor(Math.random() * generated.length)
          generated = generated.slice(0, pos) + 
            CHARACTER_SETS.numbers[Math.floor(Math.random() * CHARACTER_SETS.numbers.length)] + 
            generated.slice(pos + 1)
        }
        break

      case 'pattern':
        // Alternating pattern: letter, number, symbol (if enabled)
        const types = []
        if (characterTypes.uppercase || characterTypes.lowercase) types.push('letter')
        if (characterTypes.numbers) types.push('number')
        if (characterTypes.symbols) types.push('symbol')
        if (characterTypes.special) types.push('special')

        for (let i = 0; i < length; i++) {
          const typeIndex = i % types.length
          const type = types[typeIndex]
          
          switch (type) {
            case 'letter':
              if (characterTypes.uppercase && characterTypes.lowercase) {
                const useUpper = Math.random() > 0.5
                generated += useUpper
                  ? CHARACTER_SETS.uppercase[Math.floor(Math.random() * CHARACTER_SETS.uppercase.length)]
                  : CHARACTER_SETS.lowercase[Math.floor(Math.random() * CHARACTER_SETS.lowercase.length)]
              } else if (characterTypes.uppercase) {
                generated += CHARACTER_SETS.uppercase[Math.floor(Math.random() * CHARACTER_SETS.uppercase.length)]
              } else {
                generated += CHARACTER_SETS.lowercase[Math.floor(Math.random() * CHARACTER_SETS.lowercase.length)]
              }
              break
            case 'number':
              generated += CHARACTER_SETS.numbers[Math.floor(Math.random() * CHARACTER_SETS.numbers.length)]
              break
            case 'symbol':
              generated += CHARACTER_SETS.symbols[Math.floor(Math.random() * CHARACTER_SETS.symbols.length)]
              break
            case 'special':
              generated += CHARACTER_SETS.special[Math.floor(Math.random() * CHARACTER_SETS.special.length)]
              break
          }
        }
        break

      case 'xkcd':
        // XKCD-style passphrase (word-based)
        const wordCount = Math.ceil(length / 8) // Roughly 8 chars per word
        const words = []
        for (let i = 0; i < wordCount; i++) {
          words.push(COMMON_WORDS[Math.floor(Math.random() * COMMON_WORDS.length)])
        }
        generated = words.join(' ')
        
        // Add numbers/symbols if requested
        if (characterTypes.numbers) {
          const num = CHARACTER_SETS.numbers[Math.floor(Math.random() * CHARACTER_SETS.numbers.length)]
          generated = num + generated
        }
        if (characterTypes.symbols && generated.length < length) {
          const sym = CHARACTER_SETS.symbols[Math.floor(Math.random() * CHARACTER_SETS.symbols.length)]
          generated = generated + sym
        }
        
        // Truncate or pad to desired length
        if (generated.length > length) {
          generated = generated.substring(0, length)
        } else if (generated.length < length) {
          const padding = availableChars.substring(0, length - generated.length)
          generated = generated + padding
        }
        break

      default:
        // Fallback to random
        const fallbackArray = new Uint32Array(length)
        crypto.getRandomValues(fallbackArray)
        generated = Array.from(fallbackArray)
          .map((val) => availableChars[val % availableChars.length])
          .join('')
    }

    setPassword(generated)
    setCopied(false)
  }, [algorithm, length, characterTypes])

  const copyToClipboard = async () => {
    if (!password) return
    
    try {
      await navigator.clipboard.writeText(password)
      setCopied(true)
      setTimeout(() => setCopied(false), 2000)
    } catch (err) {
      console.error('Failed to copy:', err)
    }
  }

  const toggleCharacterType = (type) => {
    setCharacterTypes(prev => ({
      ...prev,
      [type]: !prev[type]
    }))
  }

  return (
    <div className="panel p-5">
      <div className="flex justify-between items-center mb-5 flex-wrap gap-3">
        <h2 className="m-0 text-1.3em font-600 bg-gradient-to-br from-white to-red-accent bg-clip-text text-transparent">Tools</h2>
      </div>

      <div className="tools-content">
        <div className="tools-sidebar">
          <button
            className={`tool-nav-button ${activeTool === 'password-generator' ? 'active' : ''}`}
            onClick={() => setActiveTool('password-generator')}
          >
            🔐 Password Generator
          </button>
        </div>

        <div className="tools-main">
          {activeTool === 'password-generator' && (
            <div className="password-generator">
              <div className="password-generator-header">
                <h3>Password Generator</h3>
                <p className="password-generator-description">
                  Generate secure passwords with multiple algorithms and customization options
                </p>
              </div>

              <div className="password-generator-controls">
                {/* Algorithm Selection */}
                <div className="control-group">
                  <label className="control-label">Algorithm</label>
                  <div className="algorithm-selector">
                    {ALGORITHMS.map((alg) => (
                      <button
                        key={alg.id}
                        className={`algorithm-button ${algorithm === alg.id ? 'active' : ''}`}
                        onClick={() => setAlgorithm(alg.id)}
                        title={alg.description}
                      >
                        {alg.label}
                      </button>
                    ))}
                  </div>
                </div>

                {/* Length Slider */}
                <div className="control-group">
                  <label className="control-label">
                    Length: <span className="length-value">{length}</span>
                  </label>
                  <input
                    type="range"
                    min="8"
                    max="128"
                    value={length}
                    onChange={(e) => setLength(parseInt(e.target.value))}
                    className="length-slider"
                  />
                  <div className="slider-labels">
                    <span>8</span>
                    <span>128</span>
                  </div>
                </div>

                {/* Character Type Checkboxes */}
                <div className="control-group">
                  <label className="control-label">Character Types</label>
                  <div className="character-types">
                    <label className="checkbox-label">
                      <input
                        type="checkbox"
                        checked={characterTypes.uppercase}
                        onChange={() => toggleCharacterType('uppercase')}
                      />
                      <span>Uppercase (A-Z)</span>
                    </label>
                    <label className="checkbox-label">
                      <input
                        type="checkbox"
                        checked={characterTypes.lowercase}
                        onChange={() => toggleCharacterType('lowercase')}
                      />
                      <span>Lowercase (a-z)</span>
                    </label>
                    <label className="checkbox-label">
                      <input
                        type="checkbox"
                        checked={characterTypes.numbers}
                        onChange={() => toggleCharacterType('numbers')}
                      />
                      <span>Numbers (0-9)</span>
                    </label>
                    <label className="checkbox-label">
                      <input
                        type="checkbox"
                        checked={characterTypes.symbols}
                        onChange={() => toggleCharacterType('symbols')}
                      />
                      <span>Symbols (!@#$%...)</span>
                    </label>
                    <label className="checkbox-label">
                      <input
                        type="checkbox"
                        checked={characterTypes.special}
                        onChange={() => toggleCharacterType('special')}
                      />
                      <span>Special (~`"'\/)</span>
                    </label>
                  </div>
                </div>

                {/* Generate Button */}
                <button
                  className="generate-button"
                  onClick={generatePassword}
                >
                  Generate Password
                </button>

                {/* Generated Password Display */}
                {password && (() => {
                  // Calculate available character set for entropy calculation
                  let availableChars = ''
                  if (characterTypes.uppercase) availableChars += CHARACTER_SETS.uppercase
                  if (characterTypes.lowercase) availableChars += CHARACTER_SETS.lowercase
                  if (characterTypes.numbers) availableChars += CHARACTER_SETS.numbers
                  if (characterTypes.symbols) availableChars += CHARACTER_SETS.symbols
                  if (characterTypes.special) availableChars += CHARACTER_SETS.special
                  const entropy = availableChars.length > 0 
                    ? Math.round(password.length * Math.log2(availableChars.length))
                    : 0

                  return (
                    <div className="password-display">
                      <div className="password-output">
                        <input
                          type="text"
                          readOnly
                          value={password}
                          className="password-input"
                        />
                        <button
                          className={`copy-button ${copied ? 'copied' : ''}`}
                          onClick={copyToClipboard}
                          title="Copy to clipboard"
                        >
                          {copied ? '✓ Copied!' : '📋 Copy'}
                        </button>
                      </div>
                      <div className="password-stats">
                        <span>Length: {password.length}</span>
                        <span>Entropy: ~{entropy} bits</span>
                      </div>
                    </div>
                  )
                })()}
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  )
}

export default ToolsPanel

