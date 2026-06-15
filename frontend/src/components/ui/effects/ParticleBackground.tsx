import { useCallback } from 'react'
import Particles from 'react-tsparticles'
import { loadSlim } from 'tsparticles-slim'
import type { Engine } from 'tsparticles-engine'

export default function ParticleBackground() {
  const particlesInit = useCallback(async (engine: Engine) => {
    await loadSlim(engine)
  }, [])

  return (
    <div className="fixed inset-0 z-[-1] pointer-events-none">
      <Particles
        id="tsparticles"
        init={particlesInit}
        options={{
          background: { color: { value: 'transparent' } },
          fpsLimit: 30,
          particles: {
            number: {
              value: 40,
              density: { enable: true, value_area: 800 },
            },
            color: {
              value: ['#3b82f6', '#8b5cf6', '#06b6d4', '#10b981', '#f59e0b'],
            },
            shape: { type: 'circle' },
            opacity: {
              value: 0.3,
              random: true,
              anim: { enable: true, speed: 0.5, opacity_min: 0.1 },
            },
            size: { value: 2, random: true },
            move: {
              enable: true,
              speed: 0.8,
              direction: 'none',
              random: true,
              straight: false,
              outModes: { default: 'out' },
            },
          },
          detectRetina: true,
          // 👇 These two lines disable mouse interactions (fixes hover errors)
          interactivity: {
            events: {
              onHover: { enable: false },
              onClick: { enable: false },
            },
          },
        }}
      />
    </div>
  )
}