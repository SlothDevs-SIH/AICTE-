import { memo } from 'react'
import { AnimatePresence, motion, type DOMMotionComponents, type MotionProps, type Variants } from 'motion/react'

// Ported from magic ui "text-animate": same variants and timings, plain CSS classes instead of Tailwind.
type AnimationType = 'text' | 'word' | 'character' | 'line'
type AnimationVariant = 'fadeIn' | 'blurIn' | 'blurInUp' | 'blurInDown' | 'slideUp' | 'slideDown' | 'slideLeft' | 'slideRight' | 'scaleUp' | 'scaleDown'

const motionElements = {
  article: motion.article, div: motion.div, h1: motion.h1, h2: motion.h2, h3: motion.h3, h4: motion.h4,
  h5: motion.h5, h6: motion.h6, li: motion.li, p: motion.p, section: motion.section, span: motion.span,
} as const
type MotionElementType = Extract<keyof DOMMotionComponents, keyof typeof motionElements>

interface TextAnimateProps extends Omit<MotionProps, 'children'> {
  children: string
  className?: string
  segmentClassName?: string
  delay?: number
  duration?: number
  variants?: Variants
  as?: MotionElementType
  by?: AnimationType
  startOnView?: boolean
  once?: boolean
  animation?: AnimationVariant
  accessible?: boolean
}

const staggerTimings: Record<AnimationType, number> = { text: 0.06, word: 0.05, character: 0.03, line: 0.06 }

const defaultContainerVariants = {
  hidden: { opacity: 1 },
  show: { opacity: 1, transition: { delayChildren: 0, staggerChildren: 0.05 } },
  exit: { opacity: 0, transition: { staggerChildren: 0.05, staggerDirection: -1 } },
}

const defaultItemVariants: Variants = { hidden: { opacity: 0 }, show: { opacity: 1 }, exit: { opacity: 0 } }

const blurY = { y: { duration: 0.3 }, opacity: { duration: 0.4 }, filter: { duration: 0.3 } }
const spring = { duration: 0.3, scale: { type: 'spring', damping: 15, stiffness: 300 } }

const defaultItemAnimationVariants: Record<AnimationVariant, { container: Variants; item: Variants }> = {
  fadeIn: { container: defaultContainerVariants, item: { hidden: { opacity: 0, y: 20 }, show: { opacity: 1, y: 0, transition: { duration: 0.3 } }, exit: { opacity: 0, y: 20, transition: { duration: 0.3 } } } },
  blurIn: { container: defaultContainerVariants, item: { hidden: { opacity: 0, filter: 'blur(10px)' }, show: { opacity: 1, filter: 'blur(0px)', transition: { duration: 0.3 } }, exit: { opacity: 0, filter: 'blur(10px)', transition: { duration: 0.3 } } } },
  blurInUp: { container: defaultContainerVariants, item: { hidden: { opacity: 0, filter: 'blur(10px)', y: 20 }, show: { opacity: 1, filter: 'blur(0px)', y: 0, transition: blurY }, exit: { opacity: 0, filter: 'blur(10px)', y: 20, transition: blurY } } },
  blurInDown: { container: defaultContainerVariants, item: { hidden: { opacity: 0, filter: 'blur(10px)', y: -20 }, show: { opacity: 1, filter: 'blur(0px)', y: 0, transition: blurY } } },
  slideUp: { container: defaultContainerVariants, item: { hidden: { y: 20, opacity: 0 }, show: { y: 0, opacity: 1, transition: { duration: 0.3 } }, exit: { y: -20, opacity: 0, transition: { duration: 0.3 } } } },
  slideDown: { container: defaultContainerVariants, item: { hidden: { y: -20, opacity: 0 }, show: { y: 0, opacity: 1, transition: { duration: 0.3 } }, exit: { y: 20, opacity: 0, transition: { duration: 0.3 } } } },
  slideLeft: { container: defaultContainerVariants, item: { hidden: { x: 20, opacity: 0 }, show: { x: 0, opacity: 1, transition: { duration: 0.3 } }, exit: { x: -20, opacity: 0, transition: { duration: 0.3 } } } },
  slideRight: { container: defaultContainerVariants, item: { hidden: { x: -20, opacity: 0 }, show: { x: 0, opacity: 1, transition: { duration: 0.3 } }, exit: { x: 20, opacity: 0, transition: { duration: 0.3 } } } },
  scaleUp: { container: defaultContainerVariants, item: { hidden: { scale: 0.5, opacity: 0 }, show: { scale: 1, opacity: 1, transition: spring }, exit: { scale: 0.5, opacity: 0, transition: { duration: 0.3 } } } },
  scaleDown: { container: defaultContainerVariants, item: { hidden: { scale: 1.5, opacity: 0 }, show: { scale: 1, opacity: 1, transition: spring }, exit: { scale: 1.5, opacity: 0, transition: { duration: 0.3 } } } },
}

const TextAnimateBase = ({ children, delay = 0, duration = 0.3, variants, className, segmentClassName, as: Component = 'p', startOnView = true, once = false, by = 'word', animation = 'fadeIn', accessible = true, ...props }: TextAnimateProps) => {
  const MotionComponent = motionElements[Component]
  let segments: string[] = []
  switch (by) {
    case 'word': segments = children.split(/(\s+)/); break
    case 'character': segments = children.split(''); break
    case 'line': segments = children.split('\n'); break
    default: segments = [children]
  }
  const base = defaultItemAnimationVariants[animation]
  const finalVariants = variants
    ? {
        container: {
          hidden: { opacity: 0 },
          show: { opacity: 1, transition: { opacity: { duration: 0.01, delay }, delayChildren: delay, staggerChildren: duration / segments.length } },
          exit: { opacity: 0, transition: { staggerChildren: duration / segments.length, staggerDirection: -1 } },
        },
        item: variants,
      }
    : {
        container: {
          ...base.container,
          show: { ...(base.container.show as object), transition: { delayChildren: delay, staggerChildren: duration / segments.length } },
          exit: { ...(base.container.exit as object), transition: { staggerChildren: duration / segments.length, staggerDirection: -1 } },
        },
        item: base.item ?? defaultItemVariants,
      }
  return (
    <AnimatePresence mode="popLayout">
      <MotionComponent variants={finalVariants.container as Variants} initial="hidden" whileInView={startOnView ? 'show' : undefined} animate={startOnView ? undefined : 'show'} exit="exit"
        className={`ta ${className ?? ''}`.trim()} viewport={{ once }} aria-label={accessible ? children : undefined} {...props}>
        {accessible && <span className="sr">{children}</span>}
        {segments.map((segment, i) => (
          <motion.span key={`${by}-${segment}-${i}`} variants={finalVariants.item} custom={i * staggerTimings[by]}
            className={`${by === 'line' ? 'ta-block' : 'ta-seg'} ${segmentClassName ?? ''}`.trim()} aria-hidden={accessible ? true : undefined}>
            {segment}
          </motion.span>
        ))}
      </MotionComponent>
    </AnimatePresence>
  )
}

export const TextAnimate = memo(TextAnimateBase)
