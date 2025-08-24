# Input Books Directory

Place EPUB books here for video generation.

## Supported Formats
- `.epub` files
- Books should be properly formatted with chapters

## Usage
1. Place your EPUB file in this directory
2. Run the video pipeline: `python segmind_video_pipeline.py`
3. The system will automatically process chapters and generate videos

## Processing
- Each chapter becomes a separate video
- Progress is tracked in `chapter_progress.json`
- Character information is extracted and stored for consistency

## Note
Book files are excluded from version control due to copyright and file size considerations.