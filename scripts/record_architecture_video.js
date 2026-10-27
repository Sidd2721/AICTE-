// scripts/record_architecture_video.js
// Automated 1080p Video Recording for Video 2: Complete System Architecture (AICTE PS 26265)
const { chromium } = require('playwright');
const path = require('path');
const fs = require('fs');
const { execSync } = require('child_process');
const crypto = require('crypto');

const FFMPEG_PATH = 'C:\\Users\\avadu\\ffmpeg\\ffmpeg-9.0.1-essentials_build\\bin\\ffmpeg.exe';
const VIDEO_DIR = path.join(__dirname, '..', 'docs', 'media');
const HTML_FILE = path.join(__dirname, '..', 'docs', 'video2_architecture_motion_graphics.html');

if (!fs.existsSync(VIDEO_DIR)) {
  fs.mkdirSync(VIDEO_DIR, { recursive: true });
}

function getFileHash(filePath) {
  const buffer = fs.readFileSync(filePath);
  return crypto.createHash('sha256').update(buffer).digest('hex');
}

async function recordArchitectureVideo({ durationSec = 290, outputName = 'architecture_video_1080p', speedMultiplier = 1.0 }) {
  console.log(`\n======================================================`);
  console.log(`Starting Architecture Video Recording: ${outputName}`);
  console.log(`Target Duration: ${durationSec}s | Speed: ${speedMultiplier}x`);
  console.log(`======================================================\n`);

  const htmlUrl = 'file://' + path.resolve(HTML_FILE).replace(/\\/g, '/');
  const tempDir = path.join(VIDEO_DIR, 'raw_temp_' + Date.now());
  fs.mkdirSync(tempDir, { recursive: true });

  const browser = await chromium.launch({
    headless: true,
    args: ['--no-sandbox', '--disable-setuid-sandbox', '--disable-dev-shm-usage', '--use-gl=swiftshader']
  });

  const context = await browser.newContext({
    viewport: { width: 1920, height: 1080 },
    recordVideo: {
      dir: tempDir,
      size: { width: 1920, height: 1080 }
    }
  });

  const page = await context.newPage();
  await page.goto(htmlUrl, { waitUntil: 'networkidle' });
  await page.waitForTimeout(1000);

  // Configure player
  await page.evaluate(({ speed }) => {
    window.videoController.setPlaybackRate(speed);
    window.videoController.play();
  }, { speed: speedMultiplier });

  const stepIntervalMs = 500;
  const totalSteps = Math.ceil((durationSec / speedMultiplier) * (1000 / stepIntervalMs));
  console.log(`Recording progress (${totalSteps} ticks)...`);

  for (let i = 0; i <= totalSteps; i++) {
    await page.waitForTimeout(stepIntervalMs);
    const progressPct = Math.round((i / totalSteps) * 100);
    if (i % 20 === 0 || i === totalSteps) {
      const state = await page.evaluate(() => ({
        time: window.videoController.getCurrentTime(),
        scene: document.getElementById('captionSceneTag')?.textContent || ''
      }));
      console.log(`[${progressPct}%] Time: ${Math.round(state.time)}s | ${state.scene}`);
    }
  }

  await page.evaluate(() => window.videoController.pause());
  await page.waitForTimeout(1000);

  // Close context to finalize video writing
  await context.close();
  await browser.close();

  const tempFiles = fs.readdirSync(tempDir).filter(f => f.endsWith('.webm'));
  if (tempFiles.length === 0) {
    throw new Error('No recorded webm found in ' + tempDir);
  }

  const rawWebmPath = path.join(tempDir, tempFiles[0]);
  const destWebmPath = path.join(VIDEO_DIR, `${outputName}.webm`);
  const destMp4Path = path.join(VIDEO_DIR, `${outputName}.mp4`);

  fs.copyFileSync(rawWebmPath, destWebmPath);
  console.log(`Raw WebM saved: ${destWebmPath} (${(fs.statSync(destWebmPath).size / 1024 / 1024).toFixed(2)} MB)`);

  // Transcode to MP4 if ffmpeg exists
  if (fs.existsSync(FFMPEG_PATH)) {
    console.log(`Transcoding to 1080p MP4 via FFmpeg...`);
    const ffmpegCmd = `"${FFMPEG_PATH}" -y -i "${destWebmPath}" -c:v libx264 -pix_fmt yuv420p -crf 22 -preset medium -movflags +faststart "${destMp4Path}"`;
    try {
      execSync(ffmpegCmd, { stdio: 'inherit' });
      const mp4SizeMB = (fs.statSync(destMp4Path).size / 1024 / 1024).toFixed(2);
      const sha256 = getFileHash(destMp4Path);
      console.log(`Transcoding complete!`);
      console.log(`MP4 Path: ${destMp4Path}`);
      console.log(`Size: ${mp4SizeMB} MB`);
      console.log(`SHA-256: ${sha256}`);
    } catch (err) {
      console.error('FFmpeg transcode error:', err.message);
    }
  }

  // Cleanup temp dir
  fs.rmSync(tempDir, { recursive: true, force: true });
}

async function main() {
  const args = process.argv.slice(2);
  const mode = args[0] || 'preview'; // 'preview' (90s fast cut) or 'full' (290s)

  if (mode === 'full') {
    // Full 290-second run (speedMultiplier: 1.0 or 2.0)
    await recordArchitectureVideo({
      durationSec: 290,
      outputName: 'architecture_video_full_1080p',
      speedMultiplier: 2.0 // Accelerated 2x capture
    });
  } else {
    // 90-second preview judge cut covering all 7 scenes
    await recordArchitectureVideo({
      durationSec: 90,
      outputName: 'architecture_video_90s_1080p',
      speedMultiplier: 3.2
    });
  }
}

main().catch(err => {
  console.error('Fatal recording error:', err);
  process.exit(1);
});
