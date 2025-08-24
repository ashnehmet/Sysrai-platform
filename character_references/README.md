# Character References Directory

This directory stores AI-generated character reference images for consistency across videos.

## Structure
- `character_[name].png` - Reference images for each character
- Images are generated automatically on first character appearance
- Used to maintain visual consistency across multiple videos

## Database
Character information is stored in `character_database.json` which tracks:
- Character descriptions
- Image file paths  
- Creation dates
- Appearance counts

## Usage
Reference images are automatically generated and managed by the character continuity system. The pipeline ensures characters look consistent across all generated videos.

## Note
Character images are excluded from version control due to file size, but the database structure is preserved.