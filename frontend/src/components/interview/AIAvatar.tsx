import React from 'react'
import { motion, AnimatePresence } from 'framer-motion'
import { useNDPreferencesContext } from '../../context/NDPreferencesContext'

interface AIAvatarProps {
  speaking: boolean
  listening: boolean
}

const easeInOut: [number, number, number, number] = [0.42, 0, 0.58, 1]

const pulseRing = {
  idle: {
    scale: [1, 1.04, 1],
    opacity: [0.15, 0.25, 0.15],
    transition: { duration: 3, repeat: Infinity, ease: easeInOut },
  },
  listening: {
    scale: [1, 1.08, 1],
    opacity: [0.2, 0.35, 0.2],
    transition: { duration: 0.8, repeat: Infinity, ease: easeInOut },
  },
  speaking: {
    scale: [1, 1.12, 1],
    opacity: [0.25, 0.4, 0.25],
    transition: { duration: 0.6, repeat: Infinity, ease: easeInOut },
  },
}

export function AIAvatar({ speaking, listening }: AIAvatarProps) {
  const { prefs } = useNDPreferencesContext()
  const noAnim = prefs.removeAnimations

  const stateKey = speaking ? 'speaking' : listening ? 'listening' : 'idle'

  const baseColor = speaking ? '#3b82f6' : listening ? '#ef4444' : '#6b7280'

  return (
    <div className="relative select-none">
      <svg width="130" height="130" viewBox="0 0 130 130">
        {/* Outer glow ring */}
        <motion.circle
          cx="65"
          cy="65"
          r="58"
          fill="none"
          stroke={baseColor}
          strokeWidth="2"
          animate={noAnim ? false : (pulseRing as any)[stateKey]}
          initial={false}
        />

        {/* Face circle */}
        <circle cx="65" cy="65" r="52" fill={baseColor} opacity="0.08" />
        <circle cx="65" cy="65" r="52" fill="none" stroke={baseColor} strokeWidth="2.5" />

        {/* Eyes */}
        <motion.g
          animate={speaking && !noAnim ? { y: [0, -2, 0] } : {}}
          transition={{ duration: 0.4, repeat: Infinity }}
        >
          <circle cx="48" cy="55" r="4" fill={baseColor} />
          <circle cx="82" cy="55" r="4" fill={baseColor} />
          {/* Eye shine */}
          <circle cx="49.5" cy="53.5" r="1.5" fill="white" opacity="0.6" />
          <circle cx="83.5" cy="53.5" r="1.5" fill="white" opacity="0.6" />
        </motion.g>

        {/* Eyebrows */}
        <motion.g
          animate={speaking && !noAnim ? { rotate: [-2, 2, -2] } : {}}
          transition={{ duration: 0.6, repeat: Infinity }}
          style={{ originX: 65, originY: 45 }}
        >
          <line x1="41" y1="45" x2="55" y2="43" stroke={baseColor} strokeWidth="2" strokeLinecap="round" />
          <line x1="75" y1="43" x2="89" y2="45" stroke={baseColor} strokeWidth="2" strokeLinecap="round" />
        </motion.g>

        {/* Mouth */}
        <AnimatePresence mode="wait">
          {listening ? (
            <motion.g
              key="listening-mouth"
              initial={noAnim ? false : { scaleY: 0.5, opacity: 0 }}
              animate={{ scaleY: 1, opacity: 1 }}
              exit={{ scaleY: 0.5, opacity: 0 }}
              transition={{ duration: 0.2 }}
            >
              <ellipse cx="65" cy="82" rx="8" ry="6" fill={baseColor} opacity="0.15" />
              <circle cx="65" cy="82" r="3" fill={baseColor} />
            </motion.g>
          ) : (
            <motion.path
              key="speaking-mouth"
              d="M 57 82 Q 65 87 73 82"
              fill="none"
              stroke={baseColor}
              strokeWidth="2.5"
              strokeLinecap="round"
              animate={speaking && !noAnim ? { d: ['M 57 82 Q 65 87 73 82', 'M 57 80 Q 65 88 73 80', 'M 57 82 Q 65 87 73 82'] } : {}}
              transition={{ duration: 0.35, repeat: Infinity, ease: easeInOut }}
            />
          )}
        </AnimatePresence>

        {/* Speaking waveform bars */}
        <AnimatePresence>
          {speaking && (
            <motion.g
              initial={noAnim ? false : { opacity: 0 }}
              animate={{ opacity: 1 }}
              exit={{ opacity: 0 }}
              transition={{ duration: 0.2 }}
            >
              {[0, 1, 2, 3].map((i) => (
                <motion.rect
                  key={i}
                  x={100 + i * 8}
                  y={55}
                  width={4}
                  height={10}
                  rx={2}
                  fill={baseColor}
                  animate={noAnim ? false : {
                    height: [10, 22 - i * 3, 10],
                    y: [55, 48 + i * 1.5, 55],
                  }}
                  transition={{ duration: 0.5 + i * 0.08, repeat: Infinity, ease: easeInOut, delay: i * 0.1 }}
                />
              ))}
            </motion.g>
          )}
        </AnimatePresence>
      </svg>

      {/* Status label */}
      <div className="text-center mt-2">
        <span
          className="text-sm font-medium"
          style={{ color: baseColor }}
        >
          {speaking && 'Priya is speaking...'}
          {listening && 'Listening to you...'}
          {!speaking && !listening && 'Ready'}
        </span>
      </div>
    </div>
  )
}
