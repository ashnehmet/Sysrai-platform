# Output Videos Directory

This directory contains generated video files from the video pipeline.

## Structure
- Final assembled videos are saved here with timestamps
- Format: `video_YYYY-MM-DD_HH-MM-SS.mp4`
- Files are excluded from git due to size

## Usage
Videos are automatically saved here after successful pipeline execution. Check this directory for your completed videos after running:
```bash
python segmind_video_pipeline.py
```

## Note
This directory is excluded from version control to prevent large video files from being committed to the repository.