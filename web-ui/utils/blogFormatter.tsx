/**
 * Blog Content Formatter
 * Formats blog content with Word document-style formatting for titles, headings, sub-headings, and paragraphs
 */

interface FormattedElement {
  type: 'title' | 'heading' | 'subheading' | 'paragraph' | 'list' | 'text'
  content: string
  level?: number // For headings (1 = H1, 2 = H2, etc.)
}

/**
 * Parse blog content and identify structural elements
 */
function parseBlogContent(content: string): FormattedElement[] {
  const elements: FormattedElement[] = []
  const lines = content.split('\n')
  
  let i = 0
  while (i < lines.length) {
    const line = lines[i].trim()
    
    if (!line) {
      i++
      continue
    }
    
    // Detect title (usually first non-empty line, or lines with # Title pattern)
    if (i === 0 || line.match(/^#+\s+.+$/)) {
      const titleMatch = line.match(/^#+\s+(.+)$/)
      if (titleMatch) {
        const level = (line.match(/^#+/) || [''])[0].length
        elements.push({
          type: level === 1 ? 'title' : level === 2 ? 'heading' : 'subheading',
          content: titleMatch[1],
          level: level
        })
        i++
        continue
      } else if (i === 0 && line.length > 0 && line.length < 100) {
        // First line might be a title without markdown
        elements.push({
          type: 'title',
          content: line
        })
        i++
        continue
      }
    }
    
    // Detect markdown headings (# Heading, ## Subheading, ### Sub-subheading)
    const headingMatch = line.match(/^(#{1,6})\s+(.+)$/)
    if (headingMatch) {
      const level = headingMatch[1].length
      elements.push({
        type: level === 1 ? 'title' : level === 2 ? 'heading' : 'subheading',
        content: headingMatch[2],
        level: level
      })
      i++
      continue
    }
    
    // Detect bold text that might be headings (Word style: **Heading**)
    const boldMatch = line.match(/^\*\*(.+?)\*\*$/)
    if (boldMatch && line.length < 80) {
      elements.push({
        type: 'heading',
        content: boldMatch[1]
      })
      i++
      continue
    }
    
    // Detect numbered or bulleted lists
    if (line.match(/^[\d\-\*\+]\s+.+$/)) {
      const listItems: string[] = []
      while (i < lines.length && lines[i].trim().match(/^[\d\-\*\+]\s+.+$/)) {
        listItems.push(lines[i].trim().replace(/^[\d\-\*\+]\s+/, ''))
        i++
      }
      elements.push({
        type: 'list',
        content: listItems.join('\n')
      })
      continue
    }
    
    // Regular paragraph
    if (line.length > 0) {
      // Check if it's a short line that might be a subheading
      if (line.length < 80 && !line.match(/[.!?]$/)) {
        // Could be a subheading, but also could be a short paragraph
        // Check next line to determine
        const nextLine = i + 1 < lines.length ? lines[i + 1].trim() : ''
        if (nextLine.length > 0 && !nextLine.match(/^[\d\-\*\+]/)) {
          elements.push({
            type: 'subheading',
            content: line
          })
          i++
          continue
        }
      }
      
      // Regular paragraph
      elements.push({
        type: 'paragraph',
        content: line
      })
    }
    
    i++
  }
  
  return elements
}

/**
 * Format blog content with Word document-style formatting
 */
export function formatBlogContent(content: string): JSX.Element {
  if (!content || !content.trim()) {
    return <div className="text-gray-400 italic">No content available</div>
  }
  
  const elements = parseBlogContent(content)
  
  if (elements.length === 0) {
    // Fallback: display as plain text with basic formatting
    return (
      <div className="text-gray-300 leading-relaxed whitespace-pre-wrap break-words">
        {content}
      </div>
    )
  }
  
  return (
    <div className="blog-content word-style-formatting">
      {elements.map((element, index) => {
        switch (element.type) {
          case 'title':
            return (
              <h1
                key={index}
                className="blog-title text-3xl sm:text-4xl font-bold text-white mb-6 mt-8 first:mt-0 leading-tight"
                style={{
                  fontFamily: 'Georgia, "Times New Roman", serif',
                  fontWeight: 700,
                  letterSpacing: '-0.02em'
                }}
              >
                {element.content}
              </h1>
            )
          
          case 'heading':
            return (
              <h2
                key={index}
                className="blog-heading text-2xl sm:text-3xl font-bold text-white mb-4 mt-8 leading-tight"
                style={{
                  fontFamily: 'Georgia, "Times New Roman", serif',
                  fontWeight: 600,
                  letterSpacing: '-0.01em'
                }}
              >
                {element.content}
              </h2>
            )
          
          case 'subheading':
            return (
              <h3
                key={index}
                className="blog-subheading text-xl sm:text-2xl font-semibold text-gray-200 mb-3 mt-6 leading-tight"
                style={{
                  fontFamily: 'Georgia, "Times New Roman", serif',
                  fontWeight: 600,
                  color: '#e5e7eb'
                }}
              >
                {element.content}
              </h3>
            )
          
          case 'list':
            return (
              <ul
                key={index}
                className="blog-list list-disc list-inside mb-4 ml-4 space-y-2 text-gray-300"
                style={{
                  fontFamily: 'Calibri, Arial, sans-serif',
                  fontSize: '1rem',
                  lineHeight: '1.6'
                }}
              >
                {element.content.split('\n').map((item, itemIndex) => (
                  <li key={itemIndex} className="ml-2">
                    {item}
                  </li>
                ))}
              </ul>
            )
          
          case 'paragraph':
            return (
              <p
                key={index}
                className="blog-paragraph mb-4 text-gray-300 leading-relaxed"
                style={{
                  fontFamily: 'Calibri, Arial, sans-serif',
                  fontSize: '1rem',
                  lineHeight: '1.75',
                  textAlign: 'justify',
                  textJustify: 'inter-word'
                }}
              >
                {element.content}
              </p>
            )
          
          default:
            return (
              <div
                key={index}
                className="blog-text mb-4 text-gray-300 leading-relaxed"
              >
                {element.content}
              </div>
            )
        }
      })}
    </div>
  )
}

/**
 * Check if content appears to be blog content (has structure)
 */
export function isBlogContent(content: string): boolean {
  if (!content || content.length < 50) return false
  
  // Check for common blog structure indicators
  const hasTitle = content.split('\n')[0].trim().length > 0 && content.split('\n')[0].trim().length < 100
  const hasHeadings = /^#{1,6}\s+.+$/m.test(content) || /\*\*.+?\*\*/g.test(content)
  const hasParagraphs = content.split('\n\n').length > 2
  
  return hasTitle || hasHeadings || hasParagraphs
}
