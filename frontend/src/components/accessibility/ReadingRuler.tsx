import { useEffect, useState } from 'react'
import { useNDPreferencesContext } from '@/context/NDPreferencesContext'

export default function ReadingRuler() {
  const { prefs } = useNDPreferencesContext()
  const [y, setY] = useState<number>(-200)

  useEffect(() => {
    if (!prefs.readingRuler) return

    function onMove(e: MouseEvent) {
      setY(e.clientY)
    }
    function onTouch(e: TouchEvent) {
      if (e.touches[0]) setY(e.touches[0].clientY)
    }

    window.addEventListener('mousemove', onMove)
    window.addEventListener('touchmove', onTouch, { passive: true })
    return () => {
      window.removeEventListener('mousemove', onMove)
      window.removeEventListener('touchmove', onTouch)
    }
  }, [prefs.readingRuler])

  if (!prefs.readingRuler) return null

  return (
    <div
      aria-hidden="true"
      className="reading-ruler"
      style={{ top: y - 28 }}
    />
  )
}
