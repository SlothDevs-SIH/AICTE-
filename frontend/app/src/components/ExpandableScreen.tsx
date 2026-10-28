import { useEffect, useState, type ReactNode } from 'react'
import { AnimatePresence, motion } from 'motion/react'

const T = { type: 'tween', ease: 'easeOut', duration: 0.35 } as const

/** A button that grows into a full-screen panel (shared layout animation); Esc or the close button folds it back. */
export function ExpandableScreen({ trigger, children }: { trigger: ReactNode; children: (close: () => void) => ReactNode }) {
  const [open, setOpen] = useState(false)
  useEffect(() => {
    if (!open) return
    const k = (e: KeyboardEvent) => e.key === 'Escape' && setOpen(false)
    document.addEventListener('keydown', k)
    const prev = document.body.style.overflow
    document.body.style.overflow = 'hidden'
    return () => { document.removeEventListener('keydown', k); document.body.style.overflow = prev }
  }, [open])
  return (
    <>
      <AnimatePresence initial={false}>
        {!open && (
          <motion.button key="t" type="button" layoutId="cta-card" className="xs-trigger" style={{ borderRadius: 100 }} transition={T} onClick={() => setOpen(true)}>
            <motion.span layout="position">{trigger}</motion.span>
          </motion.button>
        )}
      </AnimatePresence>
      <AnimatePresence>
        {open && (
          <motion.div key="c" layoutId="cta-card" className="xs-content" style={{ borderRadius: 24 }} transition={T} role="dialog" aria-modal="true" aria-label="Sign in">
            <motion.div className="xs-inner" initial={{ opacity: 0, y: 16 }} animate={{ opacity: 1, y: 0, transition: { delay: 0.25, duration: 0.3 } }} exit={{ opacity: 0, transition: { duration: 0.1 } }}>
              <button type="button" className="xs-close" onClick={() => setOpen(false)} aria-label="Close">✕ <span>Esc</span></button>
              {children(() => setOpen(false))}
            </motion.div>
          </motion.div>
        )}
      </AnimatePresence>
    </>
  )
}
