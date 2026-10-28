import type { ReactNode } from 'react'
import { Link } from 'react-router-dom'

// Ported from the cult-ui "organic-button" (shadcn registry): same SVG end walls and hover motion,
// written with plain CSS classes (see "organic button" in index.css) because this project does not use Tailwind.
type Props = {
  label: string
  icon?: ReactNode
  to?: string
  href?: string
  onClick?: () => void
  type?: 'button' | 'submit'
  disabled?: boolean
  size?: 'sm' | 'md' | 'lg'
  variantColor?: 'primary' | 'secondary'
  className?: string
}

const Svg = ({ w, d, cls }: { w: number; d: string; cls: string }) => (
  <svg aria-hidden="true" className={cls} fill="none" viewBox={`0 0 ${w} 40`} xmlns="http://www.w3.org/2000/svg" preserveAspectRatio="xMidYMid meet"><path d={d} /></svg>
)
const ArrowUpRight = () => (
  <svg className="ob-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true"><path d="M7 7h10v10" /><path d="M7 17 17 7" /></svg>
)

export function OrganicButton({ label, icon = <ArrowUpRight />, to, href, onClick, type = 'button', disabled, size = 'md', variantColor = 'primary', className = '' }: Props) {
  const inner = (
    <span className="ob-row">
      <span className="ob-main">
        <Svg w={10} cls="ob-svg ob-mr" d="M10 40V0H6C2.68629 0 0 2.68629 0 6V34C0 37.3137 2.68629 40 6 40H10Z" />
        <span className="ob-fill ob-text"><span className="ob-label">{label}</span></span>
        <Svg w={18} cls="ob-svg ob-ml" d="M10.899 0H0V40H2C4.40603 40 6.55968 38.5075 7.4045 36.2547L17.4533 9.45786C19.1694 4.88161 15.7864 0 10.899 0Z" />
      </span>
      <span className="ob-tail">
        <Svg w={18} cls="ob-svg ob-mr" d="M7.101 40H18V0H16C13.594 0 11.4403 1.49249 10.5955 3.74532L0.546698 30.5421C-1.1694 35.1184 2.21356 40 7.101 40Z" />
        <span className="ob-fill ob-iconbox"><span className="ob-iconpad">{icon}</span></span>
        <Svg w={10} cls="ob-svg ob-ml" d="M0 40V0H4C7.31371 0 10 2.68629 10 6V34C10 37.3137 7.31371 40 4 40H0Z" />
      </span>
    </span>
  )
  const root = `ob ob-${size} ob-${variantColor} ${className}`.trim()
  if (to) return <span className={root}><Link className="ob-a" to={to}>{inner}</Link></span>
  if (href) return <span className={root}><a className="ob-a" href={href}>{inner}</a></span>
  return <span className={root}><button className="ob-a" type={type} disabled={disabled} onClick={onClick}>{inner}</button></span>
}
