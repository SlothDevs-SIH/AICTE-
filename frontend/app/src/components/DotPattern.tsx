import { useEffect, useId, useRef, useState, type SVGProps } from 'react'
import { motion } from 'motion/react'

// Ported from magic ui "dot-pattern": the same SVG grid of dots that sizes itself to its container.
interface DotPatternProps extends Omit<SVGProps<SVGSVGElement>, 'width' | 'height' | 'x' | 'y' | 'cx' | 'cy' | 'cr'> {
  width?: number
  height?: number
  x?: number
  y?: number
  cx?: number
  cy?: number
  cr?: number
  glow?: boolean
}

export function DotPattern({ width = 16, height = 16, x = 0, y = 0, cx = 1, cy = 1, cr = 1, className = '', glow = false, ...props }: DotPatternProps) {
  const id = useId()
  const containerRef = useRef<SVGSVGElement>(null)
  const [dimensions, setDimensions] = useState({ width: 0, height: 0 })
  useEffect(() => {
    const update = () => {
      if (containerRef.current) {
        const { width: w, height: h } = containerRef.current.getBoundingClientRect()
        setDimensions({ width: w, height: h })
      }
    }
    update()
    window.addEventListener('resize', update)
    return () => window.removeEventListener('resize', update)
  }, [])
  const cols = Math.ceil(dimensions.width / width)
  const dots = Array.from({ length: cols * Math.ceil(dimensions.height / height) }, (_, i) => ({
    x: (i % cols) * width + cx + x,
    y: Math.floor(i / cols) * height + cy + y,
    delay: Math.random() * 5,
    duration: Math.random() * 3 + 2,
  }))
  return (
    <svg ref={containerRef} aria-hidden="true" className={`dotpat ${className}`.trim()} {...props}>
      <defs>
        <radialGradient id={`${id}-gradient`}>
          <stop offset="0%" stopColor="currentColor" stopOpacity="1" />
          <stop offset="100%" stopColor="currentColor" stopOpacity="0" />
        </radialGradient>
      </defs>
      {dots.map((dot) => (
        <motion.circle key={`${dot.x}-${dot.y}`} cx={dot.x} cy={dot.y} r={cr} fill={glow ? `url(#${id}-gradient)` : 'currentColor'}
          initial={glow ? { opacity: 0.4, scale: 1 } : {}}
          animate={glow ? { opacity: [0.4, 1, 0.4], scale: [1, 1.5, 1] } : {}}
          transition={glow ? { duration: dot.duration, repeat: Infinity, repeatType: 'reverse', delay: dot.delay, ease: 'easeInOut' } : {}} />
      ))}
    </svg>
  )
}

/** One fixed dotted layer behind a whole page, fading out towards the edges. */
export function DotBackdrop() {
  return <div className="dotbg" aria-hidden="true"><DotPattern width={26} height={26} cr={1.2} /></div>
}
