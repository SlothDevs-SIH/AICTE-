import { useEffect, useMemo, useRef, useState, type KeyboardEvent, type ReactNode } from 'react'
import { AnimatePresence, motion } from 'motion/react'

export interface CommandItem {
  id: string
  title: string
  section: string
  icon?: ReactNode
  shortcut?: string
  action: () => void
}

const SHARED = { type: 'tween', ease: 'easeOut', duration: 0.15 } as const
const SearchIcon = ({ size = 16 }: { size?: number }) => (
  <svg width={size} height={size} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.4" strokeLinecap="round" aria-hidden="true"><circle cx="11" cy="11" r="7" /><path d="m20 20-3.5-3.5" /></svg>
)

/** Find-anything box: press F anywhere (outside a text field) to open, type to filter, arrows and Enter to choose. */
export function CommandSearch({ items, extra }: { items: CommandItem[]; extra?: (query: string) => CommandItem[] }) {
  const [isOpen, setIsOpen] = useState(false)
  const [query, setQuery] = useState('')
  const [activeIndex, setActiveIndex] = useState(0)
  const inputRef = useRef<HTMLInputElement>(null)

  useEffect(() => {
    if (!isOpen) return
    const t = setTimeout(() => inputRef.current?.focus(), 100)
    return () => clearTimeout(t)
  }, [isOpen])

  useEffect(() => {
    const onKey = (e: globalThis.KeyboardEvent) => {
      const tag = document.activeElement?.tagName
      if (e.key.toLowerCase() === 'f' && !e.ctrlKey && !e.metaKey && !e.altKey && !isOpen && tag !== 'INPUT' && tag !== 'TEXTAREA' && tag !== 'SELECT') {
        e.preventDefault()
        setQuery('')
        setIsOpen(true)
      }
      if (e.key === 'Escape' && isOpen) { e.preventDefault(); e.stopPropagation(); setIsOpen(false) }
    }
    window.addEventListener('keydown', onKey, true)
    return () => window.removeEventListener('keydown', onKey, true)
  }, [isOpen])

  const filtered = useMemo(() => {
    const q = query.trim().toLowerCase()
    const base = items.filter((i) => i.title.toLowerCase().includes(q))
    return q && extra ? [...base, ...extra(query.trim())] : base
  }, [query, items, extra])

  useEffect(() => { requestAnimationFrame(() => setActiveIndex(0)) }, [query])

  const sections = useMemo(() => {
    const g: Record<string, CommandItem[]> = {}
    filtered.forEach((i) => { (g[i.section] ??= []).push(i) })
    return Object.entries(g).map(([name, list]) => ({ name, items: list }))
  }, [filtered])

  const choose = (i?: CommandItem) => { if (i) { i.action(); setIsOpen(false); setQuery('') } }
  const onKeyDown = (e: KeyboardEvent) => {
    if (!filtered.length) return
    if (e.key === 'ArrowDown') { e.preventDefault(); setActiveIndex((p) => (p + 1) % filtered.length) }
    else if (e.key === 'ArrowUp') { e.preventDefault(); setActiveIndex((p) => (p - 1 + filtered.length) % filtered.length) }
    else if (e.key === 'Enter') choose(filtered[activeIndex])
  }

  return (
    <>
      <AnimatePresence mode="popLayout">
        {isOpen && <motion.div className="cmd-scrim" initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }} onClick={() => setIsOpen(false)} />}
      </AnimatePresence>
      <div className="cmd-wrap">
        <AnimatePresence mode="popLayout">
          {!isOpen ? (
            <motion.button key="trigger" layoutId="command-palette" type="button" className="cmd-trigger" onClick={() => { setQuery(''); setIsOpen(true) }} transition={SHARED} aria-label="Find, shortcut F">
              <motion.span layoutId="search-icon" transition={SHARED} className="cmd-ic"><SearchIcon /></motion.span>
              <motion.span layoutId="search-text" transition={SHARED} className="cmd-ph">Find…</motion.span>
              <motion.kbd layoutId="search-shortcut" transition={SHARED} className="cmd-kbd">F</motion.kbd>
            </motion.button>
          ) : (
            <motion.div key="panel" layoutId="command-palette" className="cmd-panel" transition={SHARED} onClick={(e) => e.stopPropagation()} role="dialog" aria-label="Find">
              <div className="cmd-head">
                <motion.span layoutId="search-icon" transition={SHARED} className="cmd-ic"><SearchIcon size={18} /></motion.span>
                <div className="cmd-inwrap">
                  <input ref={inputRef} type="text" value={query} onChange={(e) => setQuery(e.target.value)} onKeyDown={onKeyDown} aria-label="Find a page or action" />
                  {!query && <motion.span layoutId="search-text" transition={SHARED} className="cmd-ph abs">Find…</motion.span>}
                </div>
                <motion.span layoutId="search-shortcut" transition={SHARED} className="cmd-kbd sm">Esc</motion.span>
              </div>
              <div className="cmd-body">
                {filtered.length === 0 ? (
                  <div className="cmd-none">Nothing matches “{query}”</div>
                ) : sections.map((s) => (
                  <div key={s.name} className="cmd-sec">
                    <h3>{s.name}</h3>
                    {s.items.map((item) => {
                      const gi = filtered.findIndex((f) => f.id === item.id)
                      return (
                        <button key={item.id} type="button" className={`cmd-item ${gi === activeIndex ? 'on' : ''}`} onMouseEnter={() => setActiveIndex(gi)} onClick={() => choose(item)}>
                          <span className="cmd-iic" aria-hidden="true">{item.icon ?? '→'}</span>
                          <span className="cmd-it">{item.title}</span>
                          {item.shortcut && <kbd>{item.shortcut}</kbd>}
                        </button>
                      )
                    })}
                  </div>
                ))}
              </div>
            </motion.div>
          )}
        </AnimatePresence>
      </div>
    </>
  )
}
