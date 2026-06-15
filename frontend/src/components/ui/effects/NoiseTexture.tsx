import { motion } from 'framer-motion'

export default function NoiseTexture() {
  return (
    <motion.div
      className="noise-overlay fixed inset-0 z-[-1] pointer-events-none"
      initial={{ opacity: 0 }}
      animate={{ opacity: 0.08 }}
      transition={{ duration: 1 }}
    />
  )
}
