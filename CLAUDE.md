# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

**STATUS**: Fully functional automated video generation pipeline with enhanced scene continuity.

Automated video generation system that creates 30-second marketing videos from EPUB books for social media (TikTok, YouTube Shorts). Uses LangGraph for orchestration with multiple AI service integrations. **Recent major improvements**: Fixed all JavaScript errors, enhanced scene continuity to eliminate jarring transitions, normalized aspect ratios, and improved fallback video generation.

**Key Achievement**: Videos now have proper narrative flow instead of abrupt 10-second scene changes.

## Essential Commands

```bash
# Activate environment and run pipeline
cd C:\video_project
venv\Scripts\activate
python segmind_video_pipeline.py

# Run batch file (shortcut)
run_daily_video.bat

# Test components before running
python test_components.py

# Start web control interface
start_web_app.bat
# Then open browser to http://localhost:5000
```

## Architecture

### Pipeline Workflow (LangGraph State Machine)
1. **source_content_node**: Reads EPUB from `input_books/`
2. **generate_script_node**: Creates 3x10-second script (GPT-4o-mini)
3. **character_manager_node**: Manages character continuity via database
4. **generate_video_clips_node**: Generates videos (Segmind Minimax Hailuo 2)
5. **generate_audio_node**: Creates voiceover (OpenAI TTS)
6. **assemble_final_video_node**: Combines clips (MoviePy 2.x)

### Key Files
- `segmind_video_pipeline.py`: Main LangGraph pipeline (**ENHANCED**: improved scene continuity)
- `web_app.py`: Flask web interface (**FIXED**: JavaScript errors, type conversion issues)
- `video_generators.py`: Multiple video API integrations (Google Veo2, RunwayML, Stability)
- `test_components.py`: Comprehensive system testing
- `character_database.json`: Character appearance tracking (17 characters)
- `chapter_progress.json`: Book processing state
- `video_scripts.db`: SQLite database for web app
- `PROJECT_SUMMARY.md`: Complete project status and achievements

### API Requirements & Status
- `SEGMIND_API_KEY`: Video/image generation (**WARNING**: Only 0.68 credits remaining)
- `OPENAI_API_KEY`: Script generation and TTS (**WORKING**)
- `GOOGLE_CLOUD_PROJECT_ID` (optional): For Google Veo2 ($15/video - premium quality)
- `RUNWAYML_API_KEY` (optional): Alternative video generation
- `STABILITY_API_KEY` (optional): Stability AI video generation

**COST COMPARISON**: Segmind $1.54/video | Google Veo2 $15/video | OpenAI TTS $0.002/video

## MoviePy 2.x Syntax

```python
# Correct MoviePy 2.x methods
clip.with_duration(10)  # NOT set_duration()
clip.with_fps(30)       # NOT set_fps()
clip.with_audio(audio)  # NOT set_audio()
TextClip(font_size=24)  # NOT fontsize=24
write_videofile(path)   # NO verbose/logger params
```

## Character Continuity System

Characters maintain consistent appearance across all videos:
- Auto-generates reference images on first appearance
- Stores in `character_references/` folder
- Database schema: `{"name": {"description", "image_path", "created_date", "appearance_count"}}`

## Scene Continuity (NEW)

Enhanced script generation ensures narrative flow:
- **Time Period Consistency**: Establishes era upfront (1940s, 1970s, modern)
- **Visual Style Matching**: Consistent clothing, architecture, vehicles
- **Scene Transitions**: Each scene picks up where previous ended
- **Setting Continuity**: Same weather, lighting, location style
- **No Abrupt Jumps**: Eliminates Biblical→1970s USA disconnects
- **9:16 Portrait Format**: All clips normalized to TikTok dimensions

## Web Interface Features

- **Script Types**: Movie style (cinematic) or UGC style (direct-to-camera)
- **Duration Control**: 20-40 seconds (not fixed 30s)
- **Review System**: Edit/approve scripts before video generation
- **Dashboard**: Track progress, view character database, manage settings

## Error Handling

- Each node updates `state['error_message']` on failure
- Graceful degradation (e.g., video without audio if TTS fails)
- Retry logic with exponential backoff for API calls
- Clean up `temp_clips/` after successful assembly

## Cost Structure

Per 30-second video:
- Character images: $0.02 (reused)
- Video clips: $1.50 (3x $0.50)
- OpenAI TTS: ~$0.002
- **Total**: ~$1.54

## Testing Workflow

1. Verify environment: `python test_components.py`
2. Check API credits (especially Segmind)
3. Place EPUB in `input_books/`
4. Run pipeline or use web interface
5. Check `output_videos/` for results

## Recent Fixes Applied (All Working)

**✅ JavaScript Errors**: Fixed "cannot read properties of undefined" in web interface
**✅ API Response Issues**: Fixed "server error, expected json" with type conversion
**✅ Scene Continuity**: Enhanced prompts eliminate Biblical→1970s jarring transitions
**✅ Aspect Ratio**: All clips normalized to 9:16 portrait (1080x1920)
**✅ Fallback Videos**: Text-based instead of blank when API fails
**✅ Variable Errors**: Fixed undefined `chapter_info` in Flask app

## Current Issues & Solutions

**⚠️ Segmind Credits Low**: 0.68 credits remaining (need 0.37+ per clip)
- **Solution**: Add credits or configure Google Veo2/RunwayML APIs

**⚠️ Video Generation Timeouts**: 30-40 minute API calls
- **Solution**: Increase timeout limits or use faster APIs

**MoviePy errors**: Use correct 2.x syntax (see above)
**FFmpeg issues**: `python -c "from moviepy.config import check; check()"`

## System Status

- **Web Interface**: ✅ Working (no JavaScript errors)  
- **Script Generation**: ✅ Working (enhanced continuity)
- **API Integration**: ✅ Working (OpenAI) | ⚠️ Low credits (Segmind)
- **Video Assembly**: ✅ Working (aspect ratio fixed)
- **Character System**: ✅ Working (17 characters loaded)

## Pydantic Notes

Use `model_dump()` not `dict()` for Pydantic models. Enhanced VideoScript model now includes continuity fields: `time_period`, `setting`, `visual_style`, `scene_transitions`.