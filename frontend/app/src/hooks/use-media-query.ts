import { useEffect, useState } from 'react'

/** Same shape as the hook the deck widget expects: isMobile is a narrow or touch-first screen. */
export function useMediaQuery() {
  const get = () => (typeof window === 'undefined' ? false : window.matchMedia('(max-width: 640px), (pointer: coarse)').matches)
  const [isMobile, setIsMobile] = useState(get)
  useEffect(() => {
    const m = window.matchMedia('(max-width: 640px), (pointer: coarse)')
    const on = () => setIsMobile(m.matches)
    m.addEventListener('change', on)
    return () => m.removeEventListener('change', on)
  }, [])
  return { isMobile }
}
