# Content Creation Crew - Web UI

A modern, sharp neon-themed single-page application for the Content Creation Crew.

## Features

- 🎨 Sharp neon calming design with glassmorphism effects
- 📝 User-friendly input panel for topic entry
- 📄 Real-time output display
- 💫 Smooth animations and transitions
- 📱 Fully responsive design
- 🚀 Built with Next.js 14 and TypeScript

## Getting Started

### Prerequisites

- Node.js 18+ installed
- npm or yarn package manager

### Installation

1. Navigate to the web-ui directory:
```bash
cd web-ui
```

2. Install dependencies:
```bash
npm install
# or
yarn install
```

3. Run the development server:
```bash
npm run dev
# or
yarn dev
```

4. Open [http://localhost:3000](http://localhost:3000) in your browser.

## Project Structure

```
web-ui/
├── app/
│   ├── api/
│   │   └── generate/
│   │       └── route.ts      # API endpoint for content generation
│   ├── globals.css           # Global styles and Tailwind config
│   ├── layout.tsx            # Root layout
│   └── page.tsx              # Main page component
├── components/
│   ├── Navbar.tsx            # Navigation bar component
│   ├── InputPanel.tsx        # Input form component
│   ├── OutputPanel.tsx       # Output display component
│   └── Footer.tsx            # Footer component
├── package.json
├── tailwind.config.js        # Tailwind CSS configuration
└── tsconfig.json             # TypeScript configuration
```

## API Integration

The UI calls the `/api/generate` endpoint which executes your CrewAI crew. Make sure:

1. Your CrewAI crew is properly configured
2. The API route has the correct path to your crew project
3. Ollama is running if using local models

## Customization

### Colors

Edit `tailwind.config.js` to customize the neon color scheme:
- `neon-cyan`: Primary accent color
- `neon-purple`: Secondary accent color
- `neon-pink`: Tertiary accent color

### Styling

Modify `app/globals.css` to adjust:
- Glass effects
- Glow animations
- Border styles
- Button effects

## Building for Production

```bash
npm run build
npm start
```

## License

MIT

