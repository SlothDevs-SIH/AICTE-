import { useState, type ReactNode } from 'react'
import { AnimatePresence, motion } from 'motion/react'
import useMeasure from 'react-use-measure'

const SPRING = { type: 'spring', stiffness: 200, damping: 22, mass: 1.2 } as const

/** Spring-animated "show details" panel: it grows to fit its content, which fades in from a blur. */
export function Expand({ title, children, defaultOpen = false }: { title: string; children: ReactNode; defaultOpen?: boolean }) {
  const [open, setOpen] = useState(defaultOpen)
  const [ref, bounds] = useMeasure({ offsetSize: true })
  return (
    <motion.div className="expand" initial={false} animate={{ height: bounds.height > 0 ? bounds.height : 'auto' }}
      transition={{ height: { ...SPRING, delay: open ? 0 : 0.05 } }}>
      <div ref={ref} className="expand-in">
        <button type="button" className="expand-head" aria-expanded={open} onClick={() => setOpen((o) => !o)}>
          <motion.span className="expand-chev" animate={{ rotate: open ? 0 : -90 }} transition={{ duration: 0.2, ease: 'easeOut' }} aria-hidden="true">⌄</motion.span>
          <span>{title}</span>
        </button>
        <AnimatePresence initial={false} mode="popLayout">
          {open && (
            <motion.div className="expand-body"
              initial={{ opacity: 0, filter: 'blur(8px)', y: 30 }}
              animate={{ opacity: 1, filter: 'blur(0px)', y: 0, transition: { type: 'spring', duration: 0.4, bounce: 0, delay: 0.15 } }}
              exit={{ opacity: 0, filter: 'blur(8px)', y: 12 }}
              transition={{ type: 'spring', duration: 0.4, bounce: 0 }}>
              {children}
            </motion.div>
          )}
        </AnimatePresence>
      </div>
    </motion.div>
  )
}
