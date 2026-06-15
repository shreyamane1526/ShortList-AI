import { motion } from 'framer-motion'
import { ReactNode } from 'react'

interface AnimatedCardProps {
  children: ReactNode
  className?: string
  delay?: number
}

const AnimatedCard = ({ children, className = '', delay = 0 }: AnimatedCardProps) => {
  return (
    <motion.div
      className={`glass-card relative hover:shadow-[0_25px_50px_rgba(0,0,0,0.25)] hover:-translate-y-2 ${className}`}
      initial={{ opacity: 0, y: 30 }}
      whileInView={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.6, ease: 'easeOut', delay }}
      whileHover={{ scale: 1.02, transition: { duration: 0.2 } }}
      viewport={{ once: true }}
    >
      {children}
    </motion.div>
  )
}

export default AnimatedCard
