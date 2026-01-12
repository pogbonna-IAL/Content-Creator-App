/**
 * Script to generate PWA icons from existing icon.svg
 * 
 * Requirements:
 * - Install sharp: npm install --save-dev sharp
 * - Run: node scripts/generate-icons.js
 * 
 * This will generate:
 * - icon-192.png (192x192)
 * - icon-512.png (512x512)
 */

const sharp = require('sharp')
const fs = require('fs')
const path = require('path')

const publicDir = path.join(__dirname, '..', 'public')
const iconSvg = path.join(publicDir, 'icon.svg')

async function generateIcons() {
  try {
    // Check if icon.svg exists
    if (!fs.existsSync(iconSvg)) {
      console.error('Error: icon.svg not found in public directory')
      console.log('Please ensure icon.svg exists before running this script')
      process.exit(1)
    }

    // Generate 192x192 icon
    await sharp(iconSvg)
      .resize(192, 192)
      .png()
      .toFile(path.join(publicDir, 'icon-192.png'))
    console.log('✓ Generated icon-192.png')

    // Generate 512x512 icon
    await sharp(iconSvg)
      .resize(512, 512)
      .png()
      .toFile(path.join(publicDir, 'icon-512.png'))
    console.log('✓ Generated icon-512.png')

    console.log('\n✓ All icons generated successfully!')
  } catch (error) {
    console.error('Error generating icons:', error)
    console.log('\nNote: If sharp is not installed, run: npm install --save-dev sharp')
    process.exit(1)
  }
}

generateIcons()

