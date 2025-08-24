# RunPod Quick Start Guide for SkyReels Video Generation

## Total Weekly Cost: $0.88 - $2.38 (vs $30+ with current APIs)

## Step 1: Create RunPod Account
1. Go to [runpod.io](https://runpod.io)
2. Sign up and add $10 credit (lasts 5-10 weeks)
3. Get $0.50 free credit for new accounts

## Step 2: Launch GPU Instance

### Recommended Configurations:

#### Option A: Budget (RTX 4090) - $0.44/hour
- Perfect for SkyReels-V1
- 24GB VRAM
- Generate 30-40 videos per hour
- **Weekly cost: $0.88 (2 hours)**

#### Option B: Performance (A100 40GB) - $0.66/hour  
- Run SkyReels-V2 with longer videos
- 40GB VRAM
- Generate 50+ videos per hour
- **Weekly cost: $1.32 (2 hours)**

### Launch Steps:
1. Click "Deploy" → "GPU Cloud"
2. Select GPU type (RTX 4090 or A100)
3. Choose "RunPod Fast PyTorch" template
4. Set "On-Demand" (not Spot for reliability)
5. Click "Deploy"

## Step 3: Connect to Instance

### Via Web Terminal:
1. Click "Connect" on your instance
2. Select "Connect to Web Terminal"

### Via SSH (Optional):
```bash
ssh root@[instance-ip] -p [port]
```

## Step 4: Install SkyReels

Copy and run in terminal:
```bash
# Download setup script
wget https://raw.githubusercontent.com/your-repo/runpod_skyreels_setup.sh
chmod +x runpod_skyreels_setup.sh

# Run setup (takes ~10 minutes)
./runpod_skyreels_setup.sh
```

## Step 5: Upload Your Content

### Option 1: Direct Upload
```bash
# In RunPod terminal
mkdir input_books
mkdir work_content

# Upload via RunPod file manager
```

### Option 2: Download from Cloud Storage
```bash
# From Google Drive
gdown https://drive.google.com/uc?id=YOUR_FILE_ID

# From Dropbox
wget https://www.dropbox.com/s/xxxxx/your_file.epub?dl=1
```

## Step 6: Run Video Generation

### For Book Videos:
```bash
cd SkyReels-V1  # or V2
python cloud_skyreels_pipeline.py
# Select: book
```

### For Work Projects:
```bash
python cloud_skyreels_pipeline.py
# Select: work
```

## Step 7: Download Results

### Via Web Interface:
1. Navigate to `batch_output/` folder
2. Select all videos
3. Click "Download"

### Via Command Line:
```bash
# Zip all videos
zip -r weekly_videos.zip batch_output/

# Download link will appear in file manager
```

## Step 8: Stop Instance (IMPORTANT!)

**Always stop when done to avoid charges:**
1. Go to RunPod dashboard
2. Click "Stop" on your instance
3. Or "Terminate" if completely done

## Time & Cost Breakdown

### Per Session (2 hours):
- Setup: 10 minutes (first time only)
- Upload content: 5 minutes
- Generate 40 videos: 90 minutes  
- Download: 5 minutes
- **Total: ~2 hours = $0.88-$1.32**

### Weekly Workflow:
- Monday: 2-hour session, generate week's videos
- Rest of week: No GPU costs
- Monthly cost: $3.52-$5.28 (vs $120+ with APIs)

## Tips for Maximum Efficiency

1. **Batch Everything**: Generate all weekly videos in one session
2. **Prepare Scripts Offline**: Have all prompts ready before starting
3. **Use Persistent Storage**: Keep models downloaded between sessions
4. **Set Reminders**: Calendar reminder to stop GPU after 2 hours
5. **Monitor Usage**: Check RunPod dashboard for real-time costs

## Troubleshooting

### Out of Memory Error:
```bash
# Enable memory optimizations
export PYTORCH_CUDA_ALLOC_CONF=max_split_size_mb:512
```

### Slow Generation:
```bash
# Check GPU utilization
nvidia-smi
```

### Can't Connect:
- Try different browser
- Check firewall settings
- Use SSH instead of web terminal

## Advanced: Automation Script

Save this as `weekly_batch.sh`:
```bash
#!/bin/bash
# Automated weekly video generation

echo "Starting weekly video batch..."

# Navigate to project
cd /workspace/SkyReels-V2

# Run generation
python cloud_skyreels_pipeline.py << EOF
book
EOF

# Auto-zip results
cd batch_output
zip -r weekly_videos_$(date +%Y%m%d).zip *.mp4

echo "Complete! Download weekly_videos_$(date +%Y%m%d).zip"
```

## Cost Comparison

| Method | Per Video | 40 Videos/Week | Monthly |
|--------|-----------|----------------|---------|
| Current (Segmind) | $1.54 | $61.60 | $246.40 |
| Google Veo2 | $15.00 | $600.00 | $2,400 |
| **RunPod + SkyReels** | **$0.02** | **$0.88** | **$3.52** |

## Next Steps

1. Test with 5 videos first
2. Optimize prompts for best quality
3. Set up weekly routine
4. Consider upgrading to A100 for longer videos
5. Share setup with work team

---

**Support Resources:**
- RunPod Discord: discord.gg/runpod
- SkyReels GitHub: github.com/SkyworkAI
- RunPod Docs: docs.runpod.io