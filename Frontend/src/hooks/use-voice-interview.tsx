import { useState, useEffect, useRef, useCallback } from "react";

interface UseVoiceInterviewProps {
  sessionId: string | null;
  onTranscript?: (text: string) => void;
  onAISpeaking?: (speaking: boolean) => void;
  onAudioReceived?: (audioBase64: string) => void;
  audioElement?: HTMLAudioElement | null;
}

export const useVoiceInterview = ({
  sessionId,
  onTranscript,
  onAISpeaking,
  onAudioReceived,
  audioElement,
}: UseVoiceInterviewProps) => {
  const [isConnected, setIsConnected] = useState(false);
  const [isListening, setIsListening] = useState(false);
  const [transcript, setTranscript] = useState("");
  const [partialTranscript, setPartialTranscript] = useState("");
  
  const wsRef = useRef<WebSocket | null>(null);
  const audioContextRef = useRef<AudioContext | null>(null);
  const processorRef = useRef<ScriptProcessorNode | null>(null);
  const streamRef = useRef<MediaStream | null>(null);
  
  const audioQueueRef = useRef<string[]>([]);
  const isPlayingRef = useRef(false);

  const log = useCallback((message: string, data?: any) => {
    console.log(`[VoiceInterview] ${message}`, data || "");
  }, []);

  const playNextInQueue = useCallback(async () => {
    if (audioQueueRef.current.length === 0 || isPlayingRef.current) return;

    const b64Data = audioQueueRef.current.shift();
    if (!b64Data) return;

    isPlayingRef.current = true;
    onAISpeaking?.(true);
    log("Playing AI response audio, queue size remaining:", audioQueueRef.current.length);

    try {
      const audioBlob = await fetch(`data:audio/mpeg;base64,${b64Data}`).then(r => r.blob());
      log("Created audio blob, size:", audioBlob.size);
      const url = URL.createObjectURL(audioBlob);

      const player = audioElement || new Audio();
      player.src = url;
      
      const onEnded = () => {
        log("Audio playback finished");
        isPlayingRef.current = false;
        onAISpeaking?.(false);
        URL.revokeObjectURL(url);
        player.removeEventListener("ended", onEnded);
        player.removeEventListener("error", onError);
        playNextInQueue();
      };

      const onError = (e: any) => {
        console.error("[VoiceInterview] Audio playback error", e);
        isPlayingRef.current = false;
        onAISpeaking?.(false);
        player.removeEventListener("ended", onEnded);
        player.removeEventListener("error", onError);
        playNextInQueue();
      };

      player.addEventListener("ended", onEnded);
      player.addEventListener("error", onError);

      log("Attempting to play audio...");
      await player.play();
      log("Audio play() started successfully");
    } catch (err) {
      console.error("[VoiceInterview] Failed to play audio", err);
      isPlayingRef.current = false;
      onAISpeaking?.(false);
      playNextInQueue();
    }
  }, [log, onAISpeaking, audioElement]);

  const startInterview = useCallback(async () => {
    if (!sessionId) {
      log("Cannot start: No session ID");
      return;
    }

    try {
      log("Requesting microphone access...");
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
      streamRef.current = stream;

      const audioCtx = new AudioContext({ sampleRate: 16000 });
      if (audioCtx.state === "suspended") {
        log("Resuming AudioContext...");
        await audioCtx.resume();
      }
      audioContextRef.current = audioCtx;
      
      const source = audioCtx.createMediaStreamSource(stream);
      const processor = audioCtx.createScriptProcessor(4096, 1, 1);
      processorRef.current = processor;

      const baseUrl = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";
      const wsProtocol = baseUrl.startsWith("https") ? "wss" : "ws";
      const wsUrl = `${wsProtocol}://${baseUrl.replace(/^https?:\/\//, "")}/ws/voice?sessionId=${sessionId}&sampleRate=16000`;
      log(`Connecting to WebSocket: ${wsUrl}`);
      
      const ws = new WebSocket(wsUrl);
      wsRef.current = ws;

      ws.onopen = () => {
        log("WebSocket connected");
        setIsConnected(true);
        setIsListening(true);
        source.connect(processor);
        processor.connect(audioCtx.destination);
      };

      ws.onmessage = (event) => {
        const data = JSON.parse(event.data);
        if (data.type === "transcript") {
          log("Final transcript received:", data.text);
          setTranscript(data.text);
          setPartialTranscript("");
          onTranscript?.(data.text);
        } else if (data.type === "partial") {
          setPartialTranscript(data.text);
        } else if (data.type === "audio") {
          log("AI audio received, adding to queue");
          audioQueueRef.current.push(data.audio);
          onAudioReceived?.(data.audio);
          playNextInQueue();
        }
      };

      ws.onclose = () => {
        log("WebSocket disconnected");
        setIsConnected(false);
        setIsListening(false);
      };

      ws.onerror = (err) => {
        console.error("WebSocket error", err);
      };

      processor.onaudioprocess = (e) => {
        if (ws.readyState === WebSocket.OPEN && !isPlayingRef.current) {
          const inputData = e.inputBuffer.getChannelData(0);
          // Convert float32 to pcm16
          const pcm16 = new Int16Array(inputData.length);
          for (let i = 0; i < inputData.length; i++) {
            pcm16[i] = Math.max(-1, Math.min(1, inputData[i])) * 0x7FFF;
          }
          ws.send(pcm16.buffer);
        }
      };

    } catch (err) {
      console.error("Failed to start voice interview", err);
    }
  }, [sessionId, log, onTranscript, onAudioReceived, playNextInQueue]);

  const stopInterview = useCallback(() => {
    log("Stopping voice interview...");
    if (wsRef.current) wsRef.current.close();
    if (processorRef.current) processorRef.current.disconnect();
    if (audioContextRef.current) audioContextRef.current.close();
    if (streamRef.current) streamRef.current.getTracks().forEach(t => t.stop());
    
    setIsConnected(false);
    setIsListening(false);
  }, [log]);

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
  };
};
