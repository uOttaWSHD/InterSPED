import { WebSocketServer } from 'ws';
import express from 'express';
import { createServer } from 'http';
import { writeFileSync, existsSync, mkdirSync } from 'fs';
import { join } from 'path';

const app = express();
const server = createServer(app);
const wss = new WebSocketServer({ server });

const STREAM_DIR = './streams';
if (!existsSync(STREAM_DIR)) {
  mkdirSync(STREAM_DIR, { recursive: true });
}

let frameCount = 0;
let lastFrameTime = Date.now();
let fps = 0;

const mjpegClients = new Set();

wss.on('connection', (ws) => {
  console.log('✅ Client connected');

  ws.on('message', (data) => {
    try {
      const message = JSON.parse(data);

      if (message.type === 'frame') {
        // Calculate FPS
        const now = Date.now();
        const elapsed = now - lastFrameTime;
        if (elapsed >= 1000) {
          fps = Math.round((frameCount * 1000) / elapsed);
          console.log(`📹 Streaming at ${fps} FPS`);
          frameCount = 0;
          lastFrameTime = now;
        }
        frameCount++;

        // Save frame as JPEG (for testing/debugging)
        if (message.data) {
          const base64Data = message.data.replace(/^data:image\/\w+;base64,/, '');
          const buffer = Buffer.from(base64Data, 'base64');

          // Stream to MJPEG clients
          if (mjpegClients.size > 0) {
            const header = `--myboundary\r\nContent-Type: image/jpeg\r\nContent-Length: ${buffer.length}\r\n\r\n`;
            mjpegClients.forEach(client => {
              try {
                client.write(header);
                client.write(buffer);
                client.write('\r\n');
              } catch (e) {
                console.error('Error sending to MJPEG client:', e);
                mjpegClients.delete(client);
              }
            });
          }

          // Save latest frame
          const framePath = join(STREAM_DIR, 'latest_frame.jpg');
          writeFileSync(framePath, buffer);
        }
      }
    } catch (error) {
      console.error('Error processing message:', error);
    }
  });

  ws.on('close', () => {
    console.log('❌ Client disconnected');
  });

  ws.on('error', (error) => {
    console.error('WebSocket error:', error);
  });
});

app.get('/health', (req, res) => {
  res.json({
    status: 'ok',
    fps,
    clients: wss.clients.size,
    mjpegClients: mjpegClients.size,
    uptime: process.uptime()
  });
});

app.get('/stream.mjpeg', (req, res) => {
  res.writeHead(200, {
    'Content-Type': 'multipart/x-mixed-replace; boundary=myboundary',
    'Cache-Control': 'no-cache',
    'Connection': 'close',
    'Pragma': 'no-cache'
  });

  mjpegClients.add(res);
  console.log(`📷 MJPEG client connected (total: ${mjpegClients.size})`);

  req.on('close', () => {
    mjpegClients.delete(res);
    console.log(`📷 MJPEG client disconnected (total: ${mjpegClients.size})`);
  });
});

app.get('/latest-frame', (req, res) => {
  const framePath = join(STREAM_DIR, 'latest_frame.jpg');
  if (existsSync(framePath)) {
    res.sendFile(framePath, { root: process.cwd() });
  } else {
    res.status(404).send('No frame available');
  }
});

const PORT = process.env.PORT || 8081;
server.listen(PORT, () => {
  console.log(`🚀 WebSocket stream server running on ws://localhost:${PORT}`);
  console.log(`🌐 HTTP server running on http://localhost:${PORT}`);
});