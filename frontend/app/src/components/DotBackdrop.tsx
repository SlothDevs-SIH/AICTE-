import { DotPattern } from '@/components/ui/dot-pattern'

/** One fixed dotted layer behind a whole page, fading out towards the edges. */
export function DotBackdrop() {
  return <div className="dotbg" aria-hidden="true"><DotPattern width={26} height={26} cr={1.2} className="text-primary/20" /></div>
}
