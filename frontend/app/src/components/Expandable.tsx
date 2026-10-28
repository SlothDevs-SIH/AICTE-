import { Children, createContext, forwardRef, useContext, useEffect, useState, type HTMLAttributes, type ReactNode } from 'react'
import { AnimatePresence, motion, useMotionValue, useSpring, type HTMLMotionProps, type TargetAndTransition } from 'motion/react'
import useMeasure from 'react-use-measure'

// Ported from cult-ui "expandable": same context, spring-measured height, presets and card layers.
// Plain CSS classes instead of Tailwind (see "expandable" in index.css).
const springConfig = { stiffness: 200, damping: 20, bounce: 0.2 }
const CHROME = 56 // padding of the card layers around the measured content
type Ease = 'easeInOut' | 'easeIn' | 'easeOut' | 'linear' | [number, number, number, number]

interface ExpandableContextType {
  isExpanded: boolean
  toggleExpand: () => void
  expandDirection: 'vertical' | 'horizontal' | 'both'
  expandBehavior: 'replace' | 'push'
  transitionDuration: number
  easeType: Ease
  initialDelay: number
}
const ExpandableContext = createContext<ExpandableContextType>({
  isExpanded: false, toggleExpand: () => {}, expandDirection: 'vertical', expandBehavior: 'replace',
  transitionDuration: 0.3, easeType: 'easeInOut', initialDelay: 0,
})
export const useExpandable = () => useContext(ExpandableContext)

interface ExpandableProps extends Omit<HTMLMotionProps<'div'>, 'children'> {
  children: ReactNode | ((props: { isExpanded: boolean }) => ReactNode)
  expanded?: boolean
  onToggle?: () => void
  transitionDuration?: number
  easeType?: Ease
  expandDirection?: 'vertical' | 'horizontal' | 'both'
  expandBehavior?: 'replace' | 'push'
  initialDelay?: number
}

export const Expandable = forwardRef<HTMLDivElement, ExpandableProps>(({ children, expanded, onToggle, transitionDuration = 0.3, easeType = 'easeInOut', expandDirection = 'vertical', expandBehavior = 'replace', initialDelay = 0, ...props }, ref) => {
  const [internal, setInternal] = useState(false)
  const isExpanded = expanded !== undefined ? expanded : internal
  const toggleExpand = onToggle || (() => setInternal((p) => !p))
  return (
    <ExpandableContext.Provider value={{ isExpanded, toggleExpand, expandDirection, expandBehavior, transitionDuration, easeType, initialDelay }}>
      <motion.div ref={ref} initial={false} transition={{ duration: transitionDuration, ease: easeType, delay: initialDelay }} {...props}>
        {typeof children === 'function' ? children({ isExpanded }) : children}
      </motion.div>
    </ExpandableContext.Provider>
  )
})
Expandable.displayName = 'Expandable'

type Preset = { initial: TargetAndTransition; animate: TargetAndTransition; exit: TargetAndTransition }
const PRESETS: Record<string, Preset> = {
  fade: { initial: { opacity: 0 }, animate: { opacity: 1 }, exit: { opacity: 0 } },
  'slide-up': { initial: { opacity: 0, y: 20 }, animate: { opacity: 1, y: 0 }, exit: { opacity: 0, y: 20 } },
  'slide-down': { initial: { opacity: 0, y: -20 }, animate: { opacity: 1, y: 0 }, exit: { opacity: 0, y: -20 } },
  scale: { initial: { opacity: 0, scale: 0.8 }, animate: { opacity: 1, scale: 1 }, exit: { opacity: 0, scale: 0.8 } },
  'blur-sm': { initial: { opacity: 0, filter: 'blur(4px)' }, animate: { opacity: 1, filter: 'blur(0px)' }, exit: { opacity: 0, filter: 'blur(4px)' } },
  'blur-md': { initial: { opacity: 0, filter: 'blur(8px)' }, animate: { opacity: 1, filter: 'blur(0px)' }, exit: { opacity: 0, filter: 'blur(8px)' } },
}

/** Wrap what should be hidden until the card is expanded. */
export const ExpandableContent = forwardRef<HTMLDivElement, Omit<HTMLMotionProps<'div'>, 'ref'> & { preset?: keyof typeof PRESETS; animateOut?: { exit?: TargetAndTransition }; stagger?: boolean; staggerChildren?: number; keepMounted?: boolean }>(
  ({ children, preset, animateOut, stagger = false, staggerChildren = 0.1, keepMounted = false, ...props }, ref) => {
    const { isExpanded, transitionDuration, easeType } = useExpandable()
    const [measureRef, { height: measured }] = useMeasure()
    const animatedHeight = useMotionValue(0)
    const smoothHeight = useSpring(animatedHeight, springConfig)
    useEffect(() => { animatedHeight.set(isExpanded ? measured : 0) }, [isExpanded, measured, animatedHeight])
    const p = preset ? PRESETS[preset] : { initial: {}, animate: {}, exit: {} }
    return (
      <motion.div ref={ref} style={{ height: smoothHeight, overflow: 'hidden' }} transition={{ duration: transitionDuration, ease: easeType }} {...props}>
        <AnimatePresence initial={false}>
          {(isExpanded || keepMounted) && (
            <motion.div ref={measureRef} initial={p.initial} animate={p.animate} exit={animateOut?.exit || p.exit} transition={{ duration: transitionDuration, ease: easeType }}>
              {stagger ? (
                <motion.div variants={{ hidden: {}, visible: { transition: { staggerChildren } } }} initial="hidden" animate="visible">
                  {Children.map(children as ReactNode, (child, i) => (
                    <motion.div key={i} variants={{ hidden: { opacity: 0, y: 20 }, visible: { opacity: 1, y: 0 } }}>{child}</motion.div>
                  ))}
                </motion.div>
              ) : children}
            </motion.div>
          )}
        </AnimatePresence>
      </motion.div>
    )
  })
ExpandableContent.displayName = 'ExpandableContent'

interface CardProps {
  children: ReactNode
  className?: string
  collapsedSize?: { width?: number; height?: number }
  expandedSize?: { width?: number; height?: number }
  hoverToExpand?: boolean
}

export const ExpandableCard = forwardRef<HTMLDivElement, CardProps>(({ children, className = '', collapsedSize = { width: 320, height: 211 }, expandedSize = { width: 480, height: undefined }, hoverToExpand = false }, ref) => {
  const { isExpanded, toggleExpand, expandDirection } = useExpandable()
  const [measureRef, { width, height }] = useMeasure()
  const animatedWidth = useMotionValue(collapsedSize.width || 0)
  const animatedHeight = useMotionValue(collapsedSize.height || 0)
  const smoothWidth = useSpring(animatedWidth, springConfig)
  const smoothHeight = useSpring(animatedHeight, springConfig)
  useEffect(() => {
    if (isExpanded) { animatedWidth.set(expandedSize.width || width); animatedHeight.set(expandedSize.height || height + CHROME) }
    else { animatedWidth.set(collapsedSize.width || width); animatedHeight.set(collapsedSize.height || height + CHROME) }
  }, [isExpanded, collapsedSize, expandedSize, width, height, animatedWidth, animatedHeight])
  return (
    <motion.div ref={ref} className={`xp ${className}`.trim()} transition={springConfig}
      style={{ width: expandDirection === 'vertical' ? collapsedSize.width : smoothWidth, height: expandDirection === 'horizontal' ? collapsedSize.height : smoothHeight }}
      onHoverStart={() => hoverToExpand && !isExpanded && toggleExpand()} onHoverEnd={() => hoverToExpand && isExpanded && toggleExpand()}>
      <div className="xp-ring">
        <div className="xp-mid">
          <div className="xp-face">
            <div className="xp-clip"><div ref={measureRef} className="xp-measure">{children}</div></div>
          </div>
        </div>
      </div>
    </motion.div>
  )
})
ExpandableCard.displayName = 'ExpandableCard'

export const ExpandableTrigger = forwardRef<HTMLDivElement, HTMLAttributes<HTMLDivElement>>(({ children, className = '', ...props }, ref) => {
  const { toggleExpand, isExpanded } = useExpandable()
  return (
    <div ref={ref} onClick={toggleExpand} onKeyDown={(e) => { if (e.key === 'Enter' || e.key === ' ') { e.preventDefault(); toggleExpand() } }}
      role="button" tabIndex={0} aria-expanded={isExpanded} className={`xp-trigger ${className}`.trim()} {...props}>{children}</div>
  )
})
ExpandableTrigger.displayName = 'ExpandableTrigger'

export const ExpandableCardHeader = forwardRef<HTMLDivElement, HTMLAttributes<HTMLDivElement>>(({ className = '', children, ...props }, ref) => (
  <div ref={ref} className={`xp-head ${className}`.trim()} {...props}><motion.div layout className="xp-headrow">{children}</motion.div></div>
))
ExpandableCardHeader.displayName = 'ExpandableCardHeader'

export const ExpandableCardContent = forwardRef<HTMLDivElement, HTMLAttributes<HTMLDivElement>>(({ className = '', children, ...props }, ref) => (
  <div ref={ref} className={`xp-content ${className}`.trim()} {...props}><motion.div layout>{children}</motion.div></div>
))
ExpandableCardContent.displayName = 'ExpandableCardContent'

export const ExpandableCardFooter = forwardRef<HTMLDivElement, HTMLAttributes<HTMLDivElement>>(({ className = '', ...props }, ref) => (
  <div ref={ref} className={`xp-foot ${className}`.trim()} {...props} />
))
ExpandableCardFooter.displayName = 'ExpandableCardFooter'
