// Global type declarations for React DevTools
declare global {
  interface Window {
    __REACT_DEVTOOLS_GLOBAL_HOOK__?: {
      renderers?: Map<any, any>
      supportsFiber?: boolean
      inject?: (renderer: any) => void
      onCommitFiberRoot?: (id: number, root: any) => void
      onCommitFiberUnmount?: (id: number) => void
      [key: string]: any
    }
  }
}

export {}

