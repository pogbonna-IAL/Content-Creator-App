import { NextResponse } from 'next/server'

/**
 * Handle Chrome DevTools configuration request
 * This prevents 404 errors in the console for DevTools requests
 */
export async function GET() {
  // Return empty JSON to satisfy Chrome DevTools
  return NextResponse.json({}, { status: 200 })
}

