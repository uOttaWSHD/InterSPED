import { useState, useEffect, useRef, useCallback } from "react";

interface UseVoiceInterviewProps {
  sessionId: string | null;
  onTranscript?: (text: string) => void;
  onAISpeaking?: (speaking: boolean) => void;
  onAudioReceived?: (audioBase64: string, aiText?: string) => void;
  audioElement?: HTMLAudioElement | null;
  isMuted?: boolean;
}

// Debug logging helper with variadic arguments
const log = (message: string, ...args: any[]) => {
  console.log(`[VoiceHook] ${message}`, ...args);
};

/**
 * Voice interview hook that handles:
 * - WebSocket connection to backend
 * - Microphone capture and audio streaming
 * - AI audio playback queue
 * - Automatic pause when AI is speaking
 */
export const useVoiceInterview = ({
  sessionId,
  onTranscript,
  onAISpeaking,
  onAudioReceived,
  audioElement,
  isMuted = false,
}: UseVoiceInterviewProps) => {
  // Connection state
  const [isConnected, setIsConnected] = useState(false);
  const [isListening, setIsListening] = useState(false);
  const [transcript, setTranscript] = useState("");
  const [partialTranscript, setPartialTranscript] = useState("");

  // Refs for callbacks to ensure stability and avoid dependency cycles
  const onTranscriptRef = useRef(onTranscript);
  const onAISpeakingRef = useRef(onAISpeaking);
  const onAudioReceivedRef = useRef(onAudioReceived);

  // Update refs when props change
  useEffect(() => {
    onTranscriptRef.current = onTranscript;
    onAISpeakingRef.current = onAISpeaking;
    onAudioReceivedRef.current = onAudioReceived;
  }, [onTranscript, onAISpeaking, onAudioReceived]);

  // Refs for audio processing (refs don't cause re-renders and are always current)
  const wsRef = useRef<WebSocket | null>(null);
  const audioContextRef = useRef<AudioContext | null>(null);
  const processorRef = useRef<ScriptProcessorNode | null>(null);
  const streamRef = useRef<MediaStream | null>(null);

  // Audio playback state
  const audioQueueRef = useRef<{ audio: string | Blob; text?: string }[]>([]);
  const isPlayingRef = useRef(false);
  const isMutedRef = useRef(isMuted);

  // Sync ref with prop
  useEffect(() => {
    isMutedRef.current = isMuted;
  }, [isMuted]);

  // Handle Mute/Unmute Logic
  useEffect(() => {
    // 1. Hardware Mute Control
    if (streamRef.current) {
      streamRef.current.getAudioTracks().forEach((track) => {
        track.enabled = !isMuted;
      });
    }

    // 2. State-Driven Protocol Actions
    if (isMuted) {
      // User Muted -> User is done speaking -> Commit to AI
      if (isConnected && wsRef.current?.readyState === WebSocket.OPEN) {
        log("User Muted: sending manual commit signal");
        wsRef.current.send(JSON.stringify({ type: "commit" }));
      }
    } else {
      // User Unmuted -> User wants to speak -> Stop AI (Interruption)
      if (isPlayingRef.current) {
        log("User Unmuted: stopping AI playback (interruption)");
        // Clear queue
        audioQueueRef.current = [];
        // Stop current audio
        if (audioElement) {
          audioElement.pause();
          audioElement.currentTime = 0;
        }
        isPlayingRef.current = false;
        // Notify that AI stopped speaking
        onAISpeakingRef.current?.(false);
      }
    }
    
    log("Mute state processed:", isMuted);
  }, [isMuted, isConnected, audioElement]);

  /**
   * Play the next audio item in the queue
   */
  const playNextInQueue = useCallback(async () => {
    if (isPlayingRef.current) return;
    if (audioQueueRef.current.length === 0) {
      onAISpeakingRef.current?.(false);
      return;
    }

    const item = audioQueueRef.current.shift();
    if (!item) return;

    isPlayingRef.current = true;
    onAISpeakingRef.current?.(true);

    try {
      let url: string;
      if (item.audio instanceof Blob) {
        url = URL.createObjectURL(item.audio);
      } else {
        const audioStr = item.audio as string;
        url = audioStr.startsWith("blob:") ? audioStr : `data:audio/mpeg;base64,${audioStr}`;
      }

      const player = audioElement || new Audio();
      player.src = url;

      const cleanup = () => {
        if (url.startsWith("blob:")) URL.revokeObjectURL(url);
        player.removeEventListener("ended", onEnded);
        player.removeEventListener("error", onError);
        isPlayingRef.current = false;
        playNextInQueue();
      };

      const onEnded = () => cleanup();
      const onError = () => cleanup();

      player.addEventListener("ended", onEnded);
      player.addEventListener("error", onError);
      await player.play();
    } catch (err) {
      isPlayingRef.current = false;
      playNextInQueue();
    }
  }, [audioElement]);

  /**
   * Manually enqueue audio for playback (e.g. TTS or Replays)
   */
  const enqueueAudio = useCallback((audio: string | Blob) => {
    audioQueueRef.current.push({ audio: audio as string });
    playNextInQueue();
  }, [playNextInQueue]);

  /**
   * Start the voice interview - connect WebSocket and start mic capture
   */
  const startInterview = useCallback(async () => {
    if (!sessionId) {
      log("Cannot start: no sessionId");
      return;
    }

    if (wsRef.current?.readyState === WebSocket.OPEN) {
      log("Already connected");
      return;
    }

    try {
      // 1. Get microphone access
      log("Requesting microphone...");
      const stream = await navigator.mediaDevices.getUserMedia({ 
        audio: {
          echoCancellation: true,
          noiseSuppression: true,
          autoGainControl: true,
        } 
      });
      
      // Apply initial mute state to tracks
      stream.getAudioTracks().forEach((track) => {
        track.enabled = !isMutedRef.current;
      });
      
      streamRef.current = stream;

      // 2. Create audio context at 16kHz (what ElevenLabs expects)
      const audioCtx = new AudioContext({ sampleRate: 16000 });
      if (audioCtx.state === "suspended") {
        await audioCtx.resume();
      }
      audioContextRef.current = audioCtx;
      log("AudioContext created, sampleRate:", audioCtx.sampleRate);

      // 3. Create audio processing chain
      const source = audioCtx.createMediaStreamSource(stream);
      const processor = audioCtx.createScriptProcessor(4096, 1, 1);
      processorRef.current = processor;

      // 4. Connect to backend WebSocket
      const baseUrl = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8001";
      const wsProtocol = baseUrl.startsWith("https") ? "wss" : "ws";
      const host = baseUrl.replace(/^https?:\/\//, "");
      const wsUrl = `${wsProtocol}://${host}/ws/voice?sessionId=${sessionId}&sampleRate=16000`;
      log("Connecting to:", wsUrl);

      const ws = new WebSocket(wsUrl);
      wsRef.current = ws;

      ws.onopen = () => {
        log("WebSocket connected");
        setIsConnected(true);
        setIsListening(true);
        // Start audio processing after connection
        source.connect(processor);
        processor.connect(audioCtx.destination);
      };

      ws.onclose = (e) => {
        log("WebSocket closed:", e.code, e.reason);
        setIsConnected(false);
        setIsListening(false);
      };

      ws.onerror = (e) => {
        console.error("[VoiceHook] WebSocket error:", e);
      };

      ws.onmessage = (event) => {
        try {
          const data = JSON.parse(event.data);

          switch (data.type) {
            case "transcript":
              log("Final transcript:", data.text);
              setTranscript(data.text);
              setPartialTranscript("");
              onTranscriptRef.current?.(data.text);
              break;

            case "partial":
              setPartialTranscript(data.text);
              break;

            case "audio":
              log("Received AI audio, text:", data.text?.substring(0, 50) + "...");
              audioQueueRef.current.push({ audio: data.audio, text: data.text });
              onAudioReceivedRef.current?.(data.audio, data.text);
              playNextInQueue();
              break;

            case "text":
              // Text-only (TTS failed)
              log("Received text-only response:", data.text);
              onAudioReceivedRef.current?.("", data.text);
              break;

            case "interrupt":
              log("Received interrupt signal - stopping playback");
              // Clear queue
              audioQueueRef.current = [];
              // Stop current audio
              if (audioElement) {
                audioElement.pause();
                audioElement.currentTime = 0;
              }
              isPlayingRef.current = false;
              onAISpeakingRef.current?.(false);
              break;

            default:
              log("Unknown message type:", data.type);
          }
        } catch (err) {
          console.error("[VoiceHook] Failed to parse message:", err);
        }
      };

      // 5. Audio processing - send PCM16 to backend
      let chunkCount = 0;
      processor.onaudioprocess = (e) => {
        // Only send if connected
        // We allow sending audio even if AI is speaking (barge-in enabled)
        // But obviously not if locally muted
        if (ws.readyState !== WebSocket.OPEN || isMutedRef.current) return;
        
        const inputData = e.inputBuffer.getChannelData(0);

        // Convert Float32 [-1, 1] to Int16 [-32768, 32767]
        const pcm16 = new Int16Array(inputData.length);
        for (let i = 0; i < inputData.length; i++) {
          const sample = Math.max(-1, Math.min(1, inputData[i]));
          pcm16[i] = sample * 0x7fff;
        }

        chunkCount++;
        if (chunkCount <= 3 || chunkCount % 100 === 0) {
          log(`Sending audio chunk #${chunkCount}, size: ${pcm16.length} samples`);
        }

        ws.send(pcm16.buffer);
      };

    } catch (err) {
      console.error("[VoiceHook] Failed to start:", err);
    }
  }, [sessionId, playNextInQueue, audioElement]);

  /**
   * Stop the voice interview - cleanup all resources
   */
  const stopInterview = useCallback(() => {
    log("Stopping interview...");

    // Close WebSocket
    if (wsRef.current) {
      wsRef.current.close();
      wsRef.current = null;
    }

    // Disconnect audio processing
    if (processorRef.current) {
      processorRef.current.disconnect();
      processorRef.current = null;
    }

    // Close audio context
    if (audioContextRef.current) {
      audioContextRef.current.close();
      audioContextRef.current = null;
    }

    // Stop microphone
    if (streamRef.current) {
      streamRef.current.getTracks().forEach((track) => track.stop());
      streamRef.current = null;
    }

    // Clear queue
    audioQueueRef.current = [];
    isPlayingRef.current = false;

    setIsConnected(false);
    setIsListening(false);
  }, []);

  // Cleanup on unmount
  useEffect(() => {
    return () => {
      stopInterview();
    };
  }, [stopInterview]);

  return {
    isConnected,
    isListening,
    transcript,
    partialTranscript,
    startInterview,
    stopInterview,
    enqueueAudio,
  };
};
