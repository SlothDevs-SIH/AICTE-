import { useEffect, useRef, useState } from 'react'
import { AnimatePresence, motion, type Variants } from 'motion/react'

export interface MenuItem {
  id: string
  label: string
  to?: string
  icon?: string
  children?: MenuItem[]
}

const pathTo = (items: MenuItem[], id: string, acc: MenuItem[] = []): MenuItem[] | null => {
  for (const it of items) {
    if (it.id === id) return acc
    if (it.children) { const r = pathTo(it.children, id, [...acc, it]); if (r) return r }
  }
  return null
}

/** Drill-in menu: choosing a group slides its items in and the rest away; the breadcrumb above steps back out. */
export function TreeMenu({ menuData, activeId, onSelect }: { menuData: MenuItem[]; activeId: string | null; onSelect: (item: MenuItem) => void }) {
  const [path, setPath] = useState<MenuItem[]>(() => (activeId ? pathTo(menuData, activeId) ?? [] : []))
  const clicked = useRef<number | null>(null)

  // keep the open group in step with the page (for example after using Find)
  useEffect(() => {
    if (!activeId) return
    const p = pathTo(menuData, activeId)
    if (p && p.map((x) => x.id).join('/') !== path.map((x) => x.id).join('/')) { clicked.current = null; setPath(p) }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [activeId, menuData])

  const items = path.length === 0 ? menuData : path[path.length - 1].children || []

  const forward = (item: MenuItem, index: number) => {
    if (item.children?.length) { clicked.current = index; setPath((p) => [...p, item]) }
    else onSelect(item)
  }
  const back = (index: number) => { clicked.current = null; setPath((p) => p.slice(0, index)) }

  const container: Variants = { initial: { opacity: 0 }, animate: { opacity: 1, transition: { staggerChildren: 0.05 } }, exit: {} }
  const row: Variants = {
    initial: { opacity: 0, y: 15 },
    animate: { opacity: 1, y: 0 },
    exit: (index: number) => {
      const c = clicked.current
      if (c !== null) {
        if (index < c) return { opacity: 0, y: -80, transition: { duration: 0.3, ease: 'easeOut' } }
        if (index > c) return { opacity: 0, y: 80, transition: { duration: 0.3, ease: 'easeOut' } }
        return { opacity: 0, transition: { duration: 0.2 } }
      }
      return { opacity: 0, y: -10, transition: { duration: 0.2 } }
    },
  }

  return (
    <div className="tree">
      <div className="tree-crumbs">
        <AnimatePresence mode="popLayout">
          {path.map((item, idx) => (
            <motion.button key={`p-${item.id}`} type="button" layout="position" initial={{ opacity: 0, x: -10 }} animate={{ opacity: 1, x: 0 }} exit={{ opacity: 0, x: -5, transition: { duration: 0.3 } }}
              className="tree-crumb" onClick={() => back(idx)} style={{ marginLeft: idx * 10 }}>
              <span aria-hidden="true">↩</span>
              <motion.span layoutId={`name-${item.id}`}>{item.label}</motion.span>
            </motion.button>
          ))}
        </AnimatePresence>
      </div>
      <div className="tree-list">
        <AnimatePresence mode="popLayout">
          <motion.ul key={path.length === 0 ? 'root' : path[path.length - 1].id} variants={container} initial="initial" animate="animate" exit="exit" style={{ paddingLeft: path.length * 10 }}>
            {items.map((item, index) => {
              const group = !!item.children?.length
              return (
                <motion.li key={item.id} custom={index} variants={row}>
                  <button type="button" className={`tree-btn ${group ? 'group' : ''} ${activeId === item.id ? 'on' : ''}`} onClick={() => forward(item, index)} aria-current={activeId === item.id ? 'page' : undefined}>
                    {item.icon && <span className="tree-ic" aria-hidden="true">{item.icon}</span>}
                    <motion.span layoutId={group ? `name-${item.id}` : undefined}>{item.label}</motion.span>
                    {group && <span className="tree-more" aria-hidden="true">›</span>}
                  </button>
                </motion.li>
              )
            })}
          </motion.ul>
        </AnimatePresence>
      </div>
    </div>
  )
}
