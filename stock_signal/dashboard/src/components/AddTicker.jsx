import React, { useState } from 'react'
import { Plus, Loader } from 'lucide-react'
import { addTicker } from '../api'

export default function AddTicker({ onAdded }) {
  const [symbol, setSymbol] = useState('')
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState('')

  const handleSubmit = async (e) => {
    e.preventDefault()
    const s = symbol.trim().toUpperCase()
    if (!s) return
    setLoading(true)
    setError('')
    try {
      await addTicker(s)
      setSymbol('')
      onAdded(s)
    } catch (err) {
      setError(err.message)
    } finally {
      setLoading(false)
    }
  }

  return (
    <form onSubmit={handleSubmit} style={{ display: 'flex', gap: 8, alignItems: 'center' }}>
      <div style={{ position: 'relative' }}>
        <input
          value={symbol}
          onChange={e => { setSymbol(e.target.value.toUpperCase()); setError('') }}
          placeholder="Add ticker (e.g. AAPL)"
          maxLength={10}
          style={{
            background: '#1a1d27', border: `1px solid ${error ? '#ef4444' : '#2d3148'}`,
            borderRadius: 8, padding: '8px 12px', color: '#f1f5f9',
            fontSize: 14, width: 200, outline: 'none',
          }}
        />
        {error && (
          <div style={{
            position: 'absolute', top: '100%', left: 0, marginTop: 4,
            background: '#2a0f0f', border: '1px solid #ef4444', borderRadius: 6,
            padding: '4px 8px', fontSize: 11, color: '#ef4444', whiteSpace: 'nowrap', zIndex: 10,
          }}>{error}</div>
        )}
      </div>
      <button
        type="submit"
        disabled={loading || !symbol.trim()}
        style={{
          background: '#1d4ed8', border: 'none', borderRadius: 8,
          padding: '8px 14px', color: '#fff', cursor: 'pointer',
          display: 'flex', alignItems: 'center', gap: 6, fontSize: 14,
          opacity: loading || !symbol.trim() ? 0.5 : 1,
          transition: 'opacity 0.2s',
        }}
      >
        {loading ? <Loader size={14} className="spin" /> : <Plus size={14} />}
        Add
      </button>
    </form>
  )
}
