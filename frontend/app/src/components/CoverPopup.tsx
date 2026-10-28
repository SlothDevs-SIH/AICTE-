import { useEffect, type ReactNode } from 'react'
import { createPortal } from 'react-dom'
import { AnimatePresence, motion } from 'motion/react'

/** Pop-up with a picture on the left and the details on the right. Opens on click, closes with Esc, the X or the backdrop. */
export function CoverPopup({ open, onClose, title, subtitle, media, children }: { open: boolean; onClose: () => void; title: string; subtitle: string; media: ReactNode; children: ReactNode }) {
  useEffect(() => {
    if (!open) return
    const prev = document.body.style.overflow
    document.body.style.overflow = 'hidden'
    const k = (e: KeyboardEvent) => e.key === 'Escape' && onClose()
    document.addEventListener('keydown', k)
    return () => { document.body.style.overflow = prev; document.removeEventListener('keydown', k) }
  }, [open, onClose])
  return createPortal(
    <AnimatePresence>
      {open && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4" role="dialog" aria-modal="true" aria-label={title}>
          <motion.div className="absolute inset-0 bg-background/80 backdrop-blur-md" initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }} onClick={onClose} />
          <motion.div
            className="relative z-10 flex h-[80vh] w-full max-w-4xl flex-col overflow-hidden rounded-2xl border border-border bg-card shadow-xl md:flex-row"
            initial={{ opacity: 0, y: 40, scale: 0.94, filter: 'blur(6px)' }} animate={{ opacity: 1, y: 0, scale: 1, filter: 'blur(0px)' }}
            exit={{ opacity: 0, y: 20, scale: 0.97 }} transition={{ type: 'spring', stiffness: 260, damping: 26 }}>
            <button onClick={onClose} aria-label="Close" className="absolute right-4 top-4 z-20 flex h-8 w-8 items-center justify-center rounded-full border border-border bg-background/50 text-foreground backdrop-blur-sm transition-colors hover:bg-accent">
              <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><path d="M18 6 6 18" /><path d="m6 6 12 12" /></svg>
            </button>
            <div className="relative h-64 w-full shrink-0 overflow-hidden md:h-full md:w-1/2">{media}</div>
            <div className="flex h-full w-full flex-col overflow-y-auto p-6 sm:p-8 md:w-1/2">
              <p className="mb-3 text-xs font-medium uppercase tracking-wide text-primary">{subtitle}</p>
              <h3 className="mb-6 border-b border-border pb-4 text-2xl font-semibold tracking-tight text-foreground sm:text-3xl">{title}</h3>
              <motion.div className="grow text-sm leading-relaxed text-foreground/80" initial={{ opacity: 0, x: 20 }} animate={{ opacity: 1, x: 0 }} transition={{ delay: 0.15 }}>{children}</motion.div>
            </div>
          </motion.div>
        </div>
      )}
    </AnimatePresence>,
    document.body,
  )
}
