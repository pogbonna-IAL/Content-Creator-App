'use client'

import { useEffect } from 'react'

/**
 * Suppresses React DevTools installhook.js warnings
 * This component should be included in the root layout
 */
export default function DevToolsSuppress() {
  useEffect(() => {
    // Suppress installhook.js and React DevTools warnings
    if (typeof window !== 'undefined') {
      // Initialize React DevTools hook if it doesn't exist
      if (!window.__REACT_DEVTOOLS_GLOBAL_HOOK__) {
        window.__REACT_DEVTOOLS_GLOBAL_HOOK__ = {
          renderers: new Map(),
          supportsFiber: true,
          inject: () => {},
          onCommitFiberRoot: () => {},
          onCommitFiberUnmount: () => {},
        } as any
      }

      // Suppress console errors related to installhook
      const originalError = console.error
      console.error = (...args: any[]) => {
        const message = args[0]
        if (
          typeof message === 'string' &&
          (message.includes('installhook') ||
           message.includes('React DevTools') ||
           message.includes('Warning: ReactDOM.render') ||
           message.includes('__REACT_DEVTOOLS'))
        ) {
          // Silently ignore these warnings
          return
        }
        originalError.apply(console, args)
      }

      // Cleanup function
      return () => {
        console.error = originalError
      }
    }
  }, [])

  return null
}

