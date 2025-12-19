# Content Creator - User Guide

Welcome to Content Creator, an AI-powered content generation platform that uses multiple AI agents working together to create comprehensive, engaging content for your blog, social media, audio, and video needs.

## Table of Contents

1. [Getting Started](#getting-started)
2. [Creating Your Account](#creating-your-account)
3. [Generating Content](#generating-content)
4. [Content Types](#content-types)
5. [Managing Your Content](#managing-your-content)
6. [Tips for Best Results](#tips-for-best-results)
7. [Troubleshooting](#troubleshooting)

---

## Getting Started

### Prerequisites

Before you begin, ensure you have:
- A modern web browser (Chrome, Firefox, Safari, or Edge)
- An active internet connection
- JavaScript enabled in your browser

### Accessing the Application

1. Open your web browser
2. Navigate to the Content Creator application URL (typically `http://localhost:3000` for local installations)
3. You'll be redirected to the authentication page if you're not logged in

---

## Creating Your Account

### Step 1: Sign Up

1. On the authentication page, you'll see a **Sign Up** form
2. Enter your email address
3. Create a password (must be at least 8 characters)
4. Optionally, enter your full name
5. Click the **Sign Up** button

### Step 2: Verify Your Account

- After successful signup, you'll be automatically logged in
- Your account is created and ready to use immediately

### Alternative: Log In

If you already have an account:

1. Click on the **Log In** tab (if on the signup page)
2. Enter your email address
3. Enter your password
4. Click the **Log In** button

### OAuth Login (Optional)

You can also sign in using:
- **Google** - Click "Sign in with Google"
- **Facebook** - Click "Sign in with Facebook" (if available)
- **GitHub** - Click "Sign in with GitHub" (if available)

---

## Generating Content

### Step 1: Enter Your Topic

1. Once logged in, you'll see the main dashboard
2. In the **Input Panel** on the left side, you'll find a text area labeled "Topic"
3. Enter a clear, specific topic for your content
   - **Good examples:**
     - "The benefits of renewable energy for small businesses"
     - "Latest trends in artificial intelligence for 2024"
     - "How to start a successful e-commerce business"
   - **Avoid vague topics:**
     - "Technology" (too broad)
     - "Stuff" (not specific)

### Step 2: Select Content Type

Use the **Features** dropdown in the navigation bar to select what type of content you want to generate:

- **Blog Post** - Comprehensive long-form articles
- **Social Media** - Posts optimized for social platforms
- **Audio** - Scripts and content for audio content
- **Video** - Scripts and outlines for video content

### Step 3: Generate Content

1. After entering your topic, click the **Generate Content** button
2. You'll see a loading indicator and status messages showing progress:
   - "Initializing crew..."
   - "Crew initialized. Starting research..."
   - "Content generation completed. Extracting content..."
3. Content will stream in real-time as it's generated
4. A progress bar shows the completion percentage

### Step 4: Review Your Content

- Once generation is complete, your content will appear in the **Output Panel** on the right
- The content is automatically saved and displayed
- You can scroll through the full content

---

## Content Types

### Blog Posts

- **Best for:** Long-form articles, blog posts, articles
- **Features:**
  - Comprehensive research and analysis
  - Well-structured with introduction, body, and conclusion
  - Detailed insights and key points
  - Professional writing style

### Social Media Content

- **Best for:** Social media posts, tweets, LinkedIn posts
- **Features:**
  - Optimized for social platforms
  - Engaging and shareable format
  - Concise and impactful messaging
  - Platform-appropriate formatting

### Audio Content

- **Best for:** Podcast scripts, audio narrations, voice-over scripts
- **Features:**
  - Conversational tone
  - Natural speech patterns
  - Clear structure for audio delivery
  - Engaging storytelling elements

### Video Content

- **Best for:** Video scripts, YouTube content, video outlines
- **Features:**
  - Visual descriptions and scene setups
  - Engaging hooks and transitions
  - Structured for video production
  - Action-oriented language

---

## Managing Your Content

### Viewing Different Content Types

1. Use the **Features** dropdown in the navigation bar
2. Select the content type you want to view:
   - Blog
   - Social Media
   - Audio
   - Video
3. The output panel will switch to show the corresponding content

### Copying Content

1. Select the text you want to copy
2. Right-click and choose "Copy" or use `Ctrl+C` (Windows/Linux) or `Cmd+C` (Mac)
3. Paste it into your desired application

### Starting a New Generation

1. Clear the current topic in the input field
2. Enter a new topic
3. Click **Generate Content** again
4. The previous content will be replaced with the new generation

---

## Tips for Best Results

### 1. Be Specific with Topics

- ✅ **Good:** "5 ways to improve productivity using AI tools in 2024"
- ❌ **Bad:** "Productivity"

### 2. Provide Context

Include relevant details:
- Target audience
- Purpose of the content
- Key points to cover
- Desired tone or style

### 3. Use Clear Language

- Write topics in plain English
- Avoid jargon unless necessary
- Be concise but descriptive

### 4. Be Patient

- Content generation can take several minutes
- The AI agents are researching and creating comprehensive content
- Don't refresh the page during generation

### 5. Review and Edit

- Always review generated content
- Edit as needed for your specific use case
- Add your personal touch and brand voice

---

## Troubleshooting

### "Authentication failed" Error

**Problem:** You see an authentication error when trying to generate content.

**Solutions:**
1. Log out and log back in
2. Clear your browser cookies and cache
3. Ensure your session hasn't expired (sessions last 7 days)
4. Try using a different browser

### "Connection terminated" Error

**Problem:** Content generation stops with a "terminated" error.

**Solutions:**
1. Check your internet connection
2. Ensure the backend server is running
3. Try generating again with a simpler topic
4. Check server logs for detailed error messages

### Content Not Generating

**Problem:** Clicking "Generate Content" doesn't start the process.

**Solutions:**
1. Ensure you've entered a topic (field is not empty)
2. Check that you're logged in (you should see your user info in the top right)
3. Refresh the page and try again
4. Check browser console for error messages

### Slow Generation

**Problem:** Content generation is taking a very long time.

**Solutions:**
1. This is normal - comprehensive content can take 5-15 minutes
2. Check the status messages for progress updates
3. Ensure Ollama is running (for local installations)
4. Try with a simpler, more focused topic

### Empty or Incomplete Content

**Problem:** Generated content is empty or seems incomplete.

**Solutions:**
1. Try generating again with a more specific topic
2. Check that all content types are selected (Blog, Social Media, etc.)
3. Review the error messages in the output panel
4. Try a different topic to test if it's topic-specific

### Can't Log In

**Problem:** Unable to log in with your credentials.

**Solutions:**
1. Verify your email and password are correct
2. Use "Forgot Password" if available
3. Try signing up with a new account
4. Check that the authentication server is running

---

## Account Management

### Viewing Your Profile

1. Click on your user avatar/name in the top right corner
2. A dropdown menu will appear showing:
   - Your name or email
   - Sign Out option

### Signing Out

1. Click on your user avatar/name in the top right
2. Click **Sign Out** from the dropdown menu
3. You'll be redirected to the login page

### Session Management

- Your login session lasts for 7 days
- You'll be automatically logged out after inactivity
- You can stay logged in across browser sessions

---

## Keyboard Shortcuts

While using the application:

- **Tab** - Navigate between form fields
- **Enter** - Submit the generation form (when topic is entered)
- **Esc** - Close modals or dropdowns
- **Ctrl/Cmd + C** - Copy selected text
- **Ctrl/Cmd + V** - Paste text

---

## Getting Help

### Contact Support

1. Click **Contact** in the navigation bar
2. Fill out the contact form
3. Submit your question or issue
4. Our team will respond as soon as possible

### About the Application

1. Click **About** in the navigation bar
2. Learn more about the application
3. View features and capabilities

---

## Best Practices

1. **Start Simple:** Begin with straightforward topics to understand how the system works
2. **Iterate:** Generate multiple versions and refine your topics
3. **Combine Content:** Use different content types together (e.g., blog post + social media posts)
4. **Customize:** Always review and personalize the generated content
5. **Save Important Content:** Copy and save content you want to keep before generating new content

---

## Frequently Asked Questions

### How long does content generation take?

Typically 5-15 minutes depending on the complexity of the topic and the type of content requested.

### Can I generate multiple pieces of content at once?

No, you can generate one piece of content at a time. Wait for the current generation to complete before starting a new one.

### Is my content saved automatically?

Content is displayed in your session but not permanently saved. Make sure to copy important content before generating new content.

### Can I edit the generated content?

Yes! The generated content is displayed as text that you can select, copy, and edit in any text editor or word processor.

### What happens if I close the browser during generation?

The generation will stop, and you'll need to start over. It's best to keep the browser open until generation completes.

### Can I use this for commercial purposes?

Check the application's terms of service and license agreement for details on commercial usage.

---

## Conclusion

You're now ready to start creating amazing content with Content Creator! Remember to:

- Be specific with your topics
- Be patient during generation
- Review and customize your content
- Experiment with different content types

Happy creating! 🚀

