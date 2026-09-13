# Jasmine & Sam — OFox setup

This branch includes `tools/jasmine_sam_generate.py`, which generates episodes 4–7 as three vertical clips each and concatenates them into a final 35-second MP4 per episode.

## 1) Set your OFox key locally

Windows PowerShell:

```powershell
$env:OFOX_API_KEY="YOUR_NEW_OFOX_KEY"
```

macOS/Linux:

```bash
export OFOX_API_KEY="YOUR_NEW_OFOX_KEY"
```

Do not commit the key to GitHub.

## 2) Optional but strongly recommended: character reference images

Upload the Jasmine/Sam reference images somewhere accessible by HTTPS, then set their URLs as a comma-separated value.

Windows PowerShell:

```powershell
$env:JASMINE_SAM_REFERENCE_URLS="https://example.com/jasmine-sam.png,https://example.com/family.png"
```

macOS/Linux:

```bash
export JASMINE_SAM_REFERENCE_URLS="https://example.com/jasmine-sam.png,https://example.com/family.png"
```

## 3) Low-cost defaults

The helper defaults to:

- model: `bytedance/seedance-2.0-mini`
- resolution: `720p`
- aspect ratio: `9:16`
- audio generation: disabled
- clip lengths: `12 + 12 + 11 = 35 seconds`
- provider route: `byteplus`

You can override with environment variables:

```bash
OFOX_VIDEO_MODEL
OFOX_RESOLUTION
OFOX_PROVIDER
OFOX_BASE_URL
```

## 4) Generate episodes 4–7

From the repository root:

```bash
python tools/jasmine_sam_generate.py 4 5 6 7
```

Output goes to:

```text
storage/jasmine_sam/episode_4/Jasmine_Sam_Episode_4.mp4
storage/jasmine_sam/episode_5/Jasmine_Sam_Episode_5.mp4
storage/jasmine_sam/episode_6/Jasmine_Sam_Episode_6.mp4
storage/jasmine_sam/episode_7/Jasmine_Sam_Episode_7.mp4
```

FFmpeg must be installed because the three generated clips are concatenated locally.

## Important

The user previously exposed an OFox API key in chat. Revoke that key and use a newly-created key locally before running the generator.
