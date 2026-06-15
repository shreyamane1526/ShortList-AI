import { useState, useEffect, useCallback } from 'react'
import { Monitor, Settings } from 'lucide-react'

const ScanlineOverlay = () => {
  const [active, setActive] = useState(false)

  useEffect(() => {
    // Load from localStorage
    const saved = localStorage.getItem('scanlines')
    if (saved) setActive(JSON.parse(saved))
  }, [])

  const toggleScanlines = useCallback(() => {
    const newActive = !active
    setActive(newActive)
    localStorage.setItem('scanlines', JSON.stringify(newActive))
  }, [active])

  return (
    <>
      {/* Toggle Button */}
      <button
        onClick={toggleScanlines}
        className="fixed top-4 right-4 z-[2] p-2 rounded-lg bg-black/50 backdrop-blur-sm text-white hover:bg-black/80 neon-glow transition-all duration-200 text-xs flex items-center gap-1 shadow-lg hover:shadow-[0_0_20px_rgba(255,255,255,0.3)]"
        title={`Retro Scanlines ${active ? 'ON' : 'OFF'} (Click to toggle)`}
        aria-label="Toggle retro scanlines"
      >
        <Monitor className="w-3 h-3" />
        {active ? 'SCAN' : 'scan'}
      </button>

      {/* Overlay */}
      <div
        className={`scanlines fixed inset-0 z-[1] pointer-events-none transition-opacity duration-300 ${
          active ? 'opacity-20' : 'opacity-0'
        }`}
        title={`Scanlines ${active ? 'ON' : 'OFF'}`}
      >
        <div className="absolute inset-0 bg-gradient-to-b from-transparent via-black/5 to-transparent" />
      </div>
    </>
  )
}

export default ScanlineOverlay

