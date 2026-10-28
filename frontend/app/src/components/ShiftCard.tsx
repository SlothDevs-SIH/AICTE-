import { useState, type ReactNode } from 'react'
import { AnimatePresence, motion } from 'motion/react'

// Ported from the cult-ui "shift-card" (shadcn registry): the title slab sits on top, the middle content swaps out on
// hover while the bottom panel grows from 38px to 194px (same timings). A tap does the same on touch screens.
export function ShiftCard({ className = '', topContent, topAnimateContent, middleContent, bottomContent }: {
  className?: string; topContent?: ReactNode; topAnimateContent?: ReactNode; middleContent?: ReactNode; bottomContent?: ReactNode
}) {
  const [hovered, setHovered] = useState(false)
  return (
    <motion.div className={`sc ${className}`} initial={{ y: 20, opacity: 0 }} animate={{ y: 0, opacity: 1 }} whileHover={{ scale: 1.02 }}
      onMouseEnter={() => setHovered(true)} onMouseLeave={() => setHovered(false)} onClick={() => setHovered((h) => !h)} onTap={() => undefined}
      tabIndex={0} onFocus={() => setHovered(true)} onBlur={() => setHovered(false)}>
      <div className="sc-head">
        <div className="sc-headin">
          {topContent}
          <AnimatePresence>{hovered ? <>{topAnimateContent}</> : null}</AnimatePresence>
        </div>
      </div>
      <div className="sc-mid"><AnimatePresence>{!hovered ? <>{middleContent}</> : null}</AnimatePresence></div>
      <motion.div className="sc-bottom" initial={{ opacity: 0, height: 0 }} animate={hovered ? { opacity: 1, height: 194 } : { opacity: 1, height: 38 }} transition={{ duration: 0.3, delay: 0.1, ease: 'circIn' }}>
        <motion.div className="sc-bottomin">{bottomContent}</motion.div>
      </motion.div>
    </motion.div>
  )
}
