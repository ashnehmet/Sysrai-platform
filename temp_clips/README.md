# Temporary Clips Directory

This directory stores individual video clips during the generation process.

## Structure
- `scene_1.mp4`, `scene_2.mp4`, etc. - Individual scene videos
- `scene_X_fallback.mp4` - Text-based fallback videos when API fails
- Files are automatically cleaned up after successful video assembly

## Usage
Temporary clips are created during video generation and combined into the final video. This directory is automatically managed by the pipeline.

## Note
This directory is excluded from version control as it contains temporary files that are cleaned up automatically.