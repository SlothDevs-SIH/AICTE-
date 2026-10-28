import { createContext, useContext, useEffect, useState, type ReactNode } from 'react'
import { createPortal } from 'react-dom'
import { AnimatePresence, motion } from 'motion/react'

// Ported from the cult-ui "expandable-screen" (shadcn registry): same context, shared layoutId morph and timings.
// Differences: plain CSS classes instead of Tailwind, an X drawn inline instead of lucide, content rendered in a
// portal so no parent can clip the full-screen panel, and Esc closes it.
interface Ctx {
  isExpanded: boolean
  expand: () => void
  collapse: () => void
  layoutId: string
  triggerRadius: string
  contentRadius: string
  animationDuration: number
}
const C = createContext<Ctx | null>(null)

export function useExpandableScreen() {
  const c = useContext(C)
  if (!c) throw new Error('useExpandableScreen must be used within an ExpandableScreen')
  return c
}

export function ExpandableScreen({ children, defaultExpanded = false, onExpandChange, layoutId = 'expandable-card', triggerRadius = '100px', contentRadius = '24px', animationDuration = 0.3, lockScroll = true }: {
  children: ReactNode; defaultExpanded?: boolean; onExpandChange?: (expanded: boolean) => void; layoutId?: string
  triggerRadius?: string; contentRadius?: string; animationDuration?: number; lockScroll?: boolean
}) {
  const [isExpanded, setIsExpanded] = useState(defaultExpanded)
  const expand = () => { setIsExpanded(true); onExpandChange?.(true) }
  const collapse = () => { setIsExpanded(false); onExpandChange?.(false) }
  useEffect(() => {
    if (!isExpanded) return
    const prev = document.body.style.overflow
    if (lockScroll) document.body.style.overflow = 'hidden'
    const k = (e: KeyboardEvent) => { if (e.key === 'Escape') { setIsExpanded(false); onExpandChange?.(false) } }
    document.addEventListener('keydown', k)
    return () => { document.removeEventListener('keydown', k); document.body.style.overflow = prev }
  }, [isExpanded, lockScroll, onExpandChange])
  return <C.Provider value={{ isExpanded, expand, collapse, layoutId, triggerRadius, contentRadius, animationDuration }}>{children}</C.Provider>
}

export function ExpandableScreenTrigger({ children, className = '' }: { children: ReactNode; className?: string }) {
  const { isExpanded, expand, layoutId, triggerRadius } = useExpandableScreen()
  return (
    <AnimatePresence initial={false}>
      {!isExpanded && (
        <motion.div className={`xs-trig ${className}`}>
          <motion.div style={{ borderRadius: triggerRadius }} layout layoutId={layoutId} className="xs-bg" />
          <motion.div initial={{ opacity: 0, scale: 0.8 }} animate={{ opacity: 1, scale: 1 }} transition={{ delay: 0.2 }} exit={{ opacity: 0, scale: 0.8 }} layout={false} onClick={expand} className="xs-face" role="button" tabIndex={0}
            onKeyDown={(e) => (e.key === 'Enter' || e.key === ' ') && (e.preventDefault(), expand())}>
            {children}
          </motion.div>
        </motion.div>
      )}
    </AnimatePresence>
  )
}

export function ExpandableScreenContent({ children, className = '', showCloseButton = true, closeButtonClassName = '' }: { children: ReactNode; className?: string; showCloseButton?: boolean; closeButtonClassName?: string }) {
  const { isExpanded, collapse, layoutId, contentRadius, animationDuration } = useExpandableScreen()
  return createPortal(
    <AnimatePresence initial={false}>
      {isExpanded && (
        <div className="xs-fixed" role="dialog" aria-modal="true">
          <motion.div layoutId={layoutId} transition={{ duration: animationDuration }} style={{ borderRadius: contentRadius }} layout className={`xs-panel ${className}`}>
            <motion.div initial={{ opacity: 0 }} animate={{ opacity: 1 }} transition={{ delay: 0.15, duration: 0.4 }} className="xs-body">{children}</motion.div>
            {showCloseButton && (
              <motion.button onClick={collapse} className={`xs-x ${closeButtonClassName}`} aria-label="Close">
                <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" aria-hidden="true"><path d="M18 6 6 18M6 6l12 12" /></svg>
              </motion.button>
            )}
          </motion.div>
        </div>
      )}
    </AnimatePresence>,
    document.body,
  )
}
