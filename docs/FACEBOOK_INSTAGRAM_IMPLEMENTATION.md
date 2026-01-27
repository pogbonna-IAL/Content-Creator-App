# Facebook and Instagram Posts Implementation

## Overview
Added Facebook and Instagram post generation to the social media content creation feature. The system now generates posts for all four major platforms: LinkedIn, Twitter/X, Facebook, and Instagram.

## Changes Made

### 1. Schema Updates (`src/content_creation_crew/schemas.py`)

**Updated `SocialMediaContentSchema`**:
- Added `facebook_post` field: 150-250 words (min_length=150, max_length=2000)
- Added `instagram_post` field: 125-2200 characters (min_length=125, max_length=2200)
- Updated `to_text()` method to include Facebook and Instagram posts in markdown output

**Character Limits**:
- **LinkedIn**: 200-300 words (professional tone)
- **Twitter/X**: <280 characters (concise)
- **Facebook**: 150-250 words (conversational, max 2000 chars)
- **Instagram**: 125-2200 characters (can include hashtags in post)

### 2. Task Configuration Updates (`src/content_creation_crew/config/tasks.yaml`)

**Updated both tasks**:
- `social_media_task`: Updated description to include Facebook and Instagram in JSON output
- `social_media_standalone_task`: Updated description to include Facebook and Instagram in JSON output

**Task Description Format**:
```yaml
Output JSON: {
  "linkedin_post": "...",
  "twitter_post": "...",
  "facebook_post": "...",
  "instagram_post": "...",
  "hashtags": [...],
  "cta": "..."
}
```

### 3. Frontend Enhancements (`web-ui/components/SocialMediaPanel.tsx`)

**Added Features**:
- JSON parsing to extract structured social media content
- Separate display sections for each platform with:
  - Platform-specific icons (LinkedIn, Twitter/X, Facebook, Instagram)
  - Color-coded headers (blue for LinkedIn, sky for Twitter, blue for Facebook, pink for Instagram)
  - Character count display for each platform
  - Hashtags displayed as styled badges
  - Call-to-action section
- Fallback to plain text display for non-JSON content (backward compatible)

**UI Improvements**:
- Each platform post is displayed in its own card
- Visual distinction between platforms
- Character limits shown for Twitter (280) and Instagram (2200)
- Hashtags displayed as clickable-style badges

## Platform-Specific Guidelines

### LinkedIn
- **Length**: 200-300 words
- **Tone**: Professional, informative
- **Format**: Paragraph-style, can include line breaks

### Twitter/X
- **Length**: <280 characters
- **Tone**: Concise, engaging
- **Format**: Single post, can include emojis

### Facebook
- **Length**: 150-250 words (max 2000 characters)
- **Tone**: Conversational, friendly
- **Format**: Paragraph-style, can include emojis

### Instagram
- **Length**: 125-2200 characters
- **Tone**: Visual, engaging, hashtag-friendly
- **Format**: Can include hashtags within the post text
- **Note**: Instagram allows hashtags in the post itself, unlike other platforms

## Testing Checklist

1. ✅ **Schema Validation**: Verify all 4 platforms are required fields
2. ✅ **Task Descriptions**: Verify LLM receives correct instructions
3. ✅ **Frontend Display**: Verify each platform displays correctly
4. ✅ **JSON Parsing**: Verify frontend correctly parses structured content
5. ✅ **Fallback Display**: Verify plain text fallback works for old format
6. ✅ **Character Limits**: Verify validation enforces platform limits
7. ✅ **Standalone Social Media**: Verify standalone generation includes all platforms
8. ✅ **Blog + Social Media**: Verify combined generation works correctly

## Backward Compatibility

- The schema changes are **not backward compatible** - existing cached content will need to be regenerated
- The frontend gracefully handles both JSON and plain text formats
- Old content will display as plain text until regenerated

## Usage

When generating social media content, the system will now automatically:
1. Generate posts for all 4 platforms (LinkedIn, Twitter/X, Facebook, Instagram)
2. Include 3-5 relevant hashtags
3. Include a call-to-action
4. Display each platform separately in the UI with platform-specific styling

## Example Output Structure

```json
{
  "linkedin_post": "Professional LinkedIn post content...",
  "twitter_post": "Concise Twitter post...",
  "facebook_post": "Conversational Facebook post...",
  "instagram_post": "Engaging Instagram post with hashtags...",
  "hashtags": ["tag1", "tag2", "tag3", "tag4", "tag5"],
  "cta": "Call-to-action text..."
}
```

## Files Modified

1. `src/content_creation_crew/schemas.py` - Added Facebook and Instagram fields
2. `src/content_creation_crew/config/tasks.yaml` - Updated task descriptions
3. `web-ui/components/SocialMediaPanel.tsx` - Enhanced UI with platform-specific display

## Next Steps (Optional Enhancements)

1. **Platform-Specific Copy Buttons**: Add individual copy buttons for each platform
2. **Platform-Specific Download**: Allow downloading individual platform posts
3. **Character Counter**: Real-time character counting during generation
4. **Platform Templates**: Pre-defined templates for each platform
5. **Hashtag Suggestions**: AI-generated hashtag suggestions based on content
