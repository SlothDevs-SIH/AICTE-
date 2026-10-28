import { useEffect, useState, type ReactNode } from 'react'
import { createPortal } from 'react-dom'
import { motion, AnimatePresence } from 'motion/react'

// The card-to-pop-up animation as supplied. Changes for this project: the photo is a `media` node (we have no images
// to use), the card text is white over the dark gradient, the pop-up is rendered in a portal so no section can
// cover it, Esc closes it, and page scrolling is locked only while it is open.
interface ExpandableCardProps {
  media: ReactNode
  title: string
  subtitle: string
  content: ReactNode
}

export default function ExpandableProfileCard({ media, title, subtitle, content }: ExpandableCardProps) {
  const [isOpen, setIsOpen] = useState(false)
  const layoutId = `expandable-profile-card-${title}`

  useEffect(() => {
    if (!isOpen) return
    const prev = document.body.style.overflow
    document.body.style.overflow = 'hidden'
    const k = (e: KeyboardEvent) => e.key === 'Escape' && setIsOpen(false)
    document.addEventListener('keydown', k)
    return () => { document.body.style.overflow = prev; document.removeEventListener('keydown', k) }
  }, [isOpen])

  return (
    <>
      <motion.div
        layoutId={layoutId}
        onClick={() => setIsOpen(true)}
        onKeyDown={(e) => (e.key === 'Enter' || e.key === ' ') && (e.preventDefault(), setIsOpen(true))}
        role="button"
        tabIndex={0}
        aria-haspopup="dialog"
        className="cursor-pointer relative h-64 w-[min(100%,330px)] overflow-hidden rounded-xl border border-border group shadow-sm"
        whileHover="hover"
      >
        <motion.div layoutId={`image-${layoutId}`} className="absolute inset-0 h-full w-full" variants={{ hover: { scale: 1.05 } }}>
          {media}
        </motion.div>
        <div className="absolute inset-0 bg-linear-to-t from-black/80 via-black/20 to-transparent opacity-80 group-hover:opacity-100 transition-opacity" />

        <div className="absolute bottom-0 left-0 p-5 sm:p-6 w-full translate-y-4 group-hover:translate-y-0 transition-transform duration-300">
          <motion.p layoutId={`subtitle-${layoutId}`} className="text-secondary text-xs font-medium tracking-wide uppercase mb-1.5">{subtitle}</motion.p>
          <motion.h3 layoutId={`title-${layoutId}`} className="text-lg sm:text-xl font-semibold tracking-tight text-white">{title}</motion.h3>
        </div>
      </motion.div>

      {createPortal(
        <AnimatePresence>
          {isOpen && (
            <div className="fixed inset-0 z-50 flex items-center justify-center p-4" role="dialog" aria-modal="true" aria-label={title}>
              <motion.div
                initial={{ opacity: 0 }}
                animate={{ opacity: 1 }}
                exit={{ opacity: 0 }}
                onClick={() => setIsOpen(false)}
                className="absolute inset-0 bg-background/80 backdrop-blur-md"
              />
              <motion.div
                layoutId={layoutId}
                className="relative w-full max-w-4xl h-[80vh] bg-card rounded-2xl overflow-hidden border border-border z-10 flex flex-col md:flex-row shadow-xl"
              >
                <button
                  onClick={() => setIsOpen(false)}
                  aria-label="Close"
                  className="absolute top-4 right-4 z-20 flex h-8 w-8 items-center justify-center bg-background/50 hover:bg-accent rounded-full border border-border text-foreground transition-colors backdrop-blur-sm"
                >
                  <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><path d="M18 6 6 18" /><path d="m6 6 12 12" /></svg>
                </button>

                <div className="relative h-64 w-full shrink-0 overflow-hidden md:h-full md:w-1/2">
                  <motion.div layoutId={`image-${layoutId}`} className="h-full w-full">{media}</motion.div>
                  <div className="absolute inset-0 bg-linear-to-t from-black/60 to-transparent md:hidden" />
                </div>

                <div className="p-6 sm:p-8 w-full md:w-1/2 flex flex-col h-full overflow-y-auto custom-scrollbar">
                  <motion.p layoutId={`subtitle-${layoutId}`} className="text-primary text-xs font-medium tracking-wide uppercase mb-3">{subtitle}</motion.p>
                  <motion.h3 layoutId={`title-${layoutId}`} className="text-2xl sm:text-3xl font-semibold tracking-tight text-foreground mb-6 pb-4 border-b border-border">{title}</motion.h3>

                  <motion.div
                    initial={{ opacity: 0, x: 20 }}
                    animate={{ opacity: 1, x: 0 }}
                    exit={{ opacity: 0, x: 10 }}
                    transition={{ delay: 0.2 }}
                    className="text-foreground/80 text-sm leading-relaxed grow"
                  >
                    {content}
                  </motion.div>
                </div>
              </motion.div>
            </div>
          )}
        </AnimatePresence>,
        document.body,
      )}
    </>
  )
}
