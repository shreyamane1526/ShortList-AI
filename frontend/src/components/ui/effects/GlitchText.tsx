import { useState, useEffect } from 'react'
import { motion, AnimatePresence } from 'framer-motion'

interface GlitchTextProps {
  children: string
  className?: string
}

const GlitchText = ({ children, className = '' }: GlitchTextProps) => {
  const [isGlitching, setIsGlitching] = useState(false)

  useEffect(() => {
    const interval = setInterval(() => {
      if (Math.random() < 0.3) {
        setIsGlitching(true)
        setTimeout(() => setIsGlitching(false), 200)
      }
    }, Math.random() * 5000 + 3000) // 3-8s random

    return () => clearInterval(interval)
  }, [])

  return (
    <motion.div
      className={className}
      initial={{ opacity: 0, y: 30 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.6, ease: 'easeOut' }}
      whileHover={{ scale: 1.02 }}
    >
      <div className="relative overflow-hidden">
        <AnimatePresence>
          {isGlitching && (
            <motion.div
              className="absolute inset-0 bg-gradient-to-r from-red-500/20 via-purple-500/20 to-blue-500/20"
              initial={{ skewX: 0 }}
              animate={{ skewX: [0, -10, 10, 0] }}
              transition={{ duration: 0.2, repeat: 2, repeatType: 'mirror' }}
              exit={{ opacity: 0 }}
            />
          )}
        </AnimatePresence>
        <motion.h1
          className="relative bg-gradient-to-r from-gray-900 to-gray-800 bg-clip-text text-transparent font-black"
          animate={isGlitching ? { x: [0, 2, -2, 0] } : {}}
          transition={isGlitching ? { duration: 0.1, repeat: 5 } : {}}
        >
          {children}
          <span className="absolute inset-0 bg-gradient-to-r from-transparent via-white/20 to-transparent animate-shimmer" />
          <span aria-hidden className="invisible select-none">{children}</span>
        </motion.h1>
      </div>
    </motion.div>
  )
}

export default GlitchText
