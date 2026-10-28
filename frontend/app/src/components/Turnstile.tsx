import { useEffect, useRef } from 'react'

declare global { interface Window { turnstile?: any; __tsLoading?: Promise<void> } }

function loadScript(): Promise<void> {
  if (window.turnstile) return Promise.resolve()
  window.__tsLoading ??= new Promise((resolve, reject) => {
    const s = document.createElement('script')
    s.src = 'https://challenges.cloudflare.com/turnstile/v0/api.js?render=explicit'
    s.async = true
    s.onload = () => resolve()
    s.onerror = () => reject(new Error('The check could not be loaded.'))
    document.head.appendChild(s)
  })
  return window.__tsLoading
}

/** The Cloudflare Turnstile check. Calls onToken with a one-time token when the visitor passes, and with '' when it expires. */
export function Turnstile({ siteKey, onToken, onError }: { siteKey: string; onToken: (t: string) => void; onError?: (m: string) => void }) {
  const box = useRef<HTMLDivElement>(null)
  useEffect(() => {
    let id: string | undefined
    let dead = false
    loadScript().then(() => {
      if (dead || !box.current) return
      id = window.turnstile.render(box.current, {
        sitekey: siteKey, theme: 'light',
        callback: (t: string) => onToken(t), 'expired-callback': () => onToken(''), 'error-callback': () => { onToken(''); onError?.('The check could not run. Reload the page and try again.') },
      })
    }).catch((e) => onError?.(e.message))
    return () => { dead = true; if (id && window.turnstile) window.turnstile.remove(id) }
  }, [siteKey])
  return <div ref={box} className="turnstile-box" />
}
