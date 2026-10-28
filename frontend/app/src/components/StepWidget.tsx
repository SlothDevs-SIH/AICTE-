import { useEffect, useState } from 'react'
import { AnimatePresence, motion, MotionConfig, type Transition } from 'motion/react'
import { Check, ClipboardCopy, X } from 'lucide-react'
import useMeasure from 'react-use-measure'

// The expanding-pill widget (a small pill that grows into a card, then folds back), with our content in it.
interface Props {
  n: number
  title: string
  summary: string
  points: string[]
}

const AnimatedText = ({ from, to, isCopied }: { from: string; to: string; isCopied: boolean }) => {
  const activeText = isCopied ? to : from
  return (
    <div className="flex text-sm font-semibold tracking-tight will-change-transform">
      <AnimatePresence mode="popLayout" initial={false}>
        {activeText.split('').map((char, index) => (
          <motion.span key={char + index} layout initial={{ opacity: 0, y: 5, scale: 0.7 }}
            animate={{ opacity: 1, y: 0, scale: 1, transition: { type: 'spring', stiffness: 200, damping: 20, delay: 0.03 * index } }}
            exit={{ opacity: 0, y: -5, scale: 0.7 }}>
            {char === ' ' ? ' ' : char}
          </motion.span>
        ))}
      </AnimatePresence>
    </div>
  )
}

export function StepWidget({ n, title, summary, points }: Props) {
  const [isExpanded, setIsExpanded] = useState(false)
  const [isCopied, setIsCopied] = useState(false)
  const [ref, bounds] = useMeasure()

  useEffect(() => {
    if (!isCopied) return
    const t = setTimeout(() => setIsCopied(false), 2000)
    return () => clearTimeout(t)
  }, [isCopied])

  const springConfig: Transition = { type: 'spring', bounce: 0.25, visualDuration: 0.35 }
  const collapsedTransition: Transition = { type: 'spring', bounce: 0.15, visualDuration: 0.35 }

  return (
    <div className="flex items-start justify-center">
      <MotionConfig transition={isExpanded ? springConfig : collapsedTransition}>
        <motion.div
          initial={{ width: 292 }}
          animate={{ width: isExpanded ? 340 : 292, height: isExpanded ? bounds.height : 52 }}
          className="max-w-full overflow-hidden rounded-[32px] bg-[#F4F4F9] text-neutral-900 shadow-[0_18px_30px_rgba(5,15,50,0.3)]"
        >
          <div ref={ref}>
            <AnimatePresence mode="popLayout" initial={false}>
              {!isExpanded ? (
                <motion.button
                  key="collapsed"
                  type="button"
                  aria-expanded={false}
                  className="flex w-full cursor-pointer items-center gap-3 px-3 py-[10px] text-left font-semibold"
                  onClick={() => setIsExpanded(true)}
                  initial={{ opacity: 0, filter: 'blur(4px)' }}
                  animate={{ opacity: 1, y: 0, filter: 'blur(0px)' }}
                  exit={{ opacity: 0, filter: 'blur(4px)' }}
                >
                  <span className="grid size-8 shrink-0 place-items-center rounded-full bg-[#ff8a2a] text-sm font-extrabold text-[#0f1f3d]">{n}</span>
                  <span className="truncate">{title}</span>
                </motion.button>
              ) : (
                <motion.div
                  key="expanded"
                  className="flex flex-col gap-3 p-4"
                  initial={{ opacity: 0 }}
                  animate={{ opacity: 1 }}
                  exit={{ opacity: 0, transition: { duration: 0.2, ease: 'easeOut' } }}
                >
                  <motion.div className="flex items-center gap-3" initial={{ opacity: 0, y: 24, scale: 1.05 }} animate={{ opacity: 1, y: 0, scale: 1 }}>
                    <span className="grid size-9 shrink-0 place-items-center rounded-full bg-[#ff8a2a] text-base font-extrabold text-[#0f1f3d]">{n}</span>
                    <h3 className="text-lg font-bold leading-tight tracking-tight">{title}</h3>
                  </motion.div>
                  <motion.p className="text-sm leading-relaxed text-neutral-600" initial={{ opacity: 0, y: 24 }} animate={{ opacity: 1, y: 0 }}>{summary}</motion.p>
                  <motion.ol className="grid gap-2 rounded-3xl border border-gray-200 bg-white p-3 text-[13px] leading-snug" initial={{ opacity: 0, y: 40, scale: 1.05 }} animate={{ opacity: 1, y: 0, scale: 1 }}>
                    {points.map((p, i) => (
                      <li key={p} className="flex gap-2">
                        <span className="mt-px grid size-5 shrink-0 place-items-center rounded-full bg-[#1a3fa8] text-[11px] font-bold text-white">{i + 1}</span>
                        <span>{p}</span>
                      </li>
                    ))}
                  </motion.ol>
                  <div className="flex w-full items-center gap-2">
                    <motion.button
                      type="button"
                      className="flex flex-1 cursor-pointer items-center justify-center gap-1.5 rounded-full border border-gray-200 bg-white p-2 font-medium"
                      onClick={() => {
                        try { navigator.clipboard.writeText(`${title}\n${summary}\n${points.map((p, i) => `${i + 1}. ${p}`).join('\n')}`) } catch { /* clipboard blocked */ }
                        setIsCopied(true)
                      }}
                      layout
                    >
                      <motion.span layout>{isCopied ? <Check className="size-4" /> : <ClipboardCopy className="size-4" />}</motion.span>
                      <AnimatedText from="Copy" to="Copied" isCopied={isCopied} />
                      <motion.span layout className="text-sm font-semibold">text</motion.span>
                    </motion.button>
                    <button
                      type="button"
                      aria-label="Close"
                      className="flex cursor-pointer items-center justify-center rounded-full border border-gray-200 bg-white p-2"
                      onClick={() => { setIsExpanded(false); setIsCopied(false) }}
                    >
                      <X className="size-5" />
                    </button>
                  </div>
                </motion.div>
              )}
            </AnimatePresence>
          </div>
        </motion.div>
      </MotionConfig>
    </div>
  )
}
