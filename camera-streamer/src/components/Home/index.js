import React, { useEffect, useRef, useState } from 'react';

const ENV_DEVICE_ID = process.env.GATSBY_CAMERA_DEVICE_ID || '';
const LS_KEY = 'cameraDeviceId';
const vidWidth = 1920;
const vidHeight = 1080;

function Home() {
  const videoRef = useRef(null);
  const streamRef = useRef(null);
  const [error, setError] = useState(null);
  const [retryTrigger, setRetryTrigger] = useState(0);

  useEffect(() => {
    let active = true;
    let retryTimeout = null;

    const deviceId = ENV_DEVICE_ID || localStorage.getItem(LS_KEY) || undefined;

    const constraints = {
      video: deviceId
        ? {
          deviceId: { exact: deviceId },
          width: { ideal: vidWidth },
          height: { ideal: vidHeight },
        }
        : { width: { ideal: vidWidth }, height: { ideal: vidHeight } },
      audio: false,
    };

    const startCamera = async () => {
      try {
        const stream = await navigator.mediaDevices.getUserMedia(constraints);

        if (!active) {
          stream.getTracks().forEach((t) => t.stop());
          return;
        }

        const videoTrack = stream.getVideoTracks()[0];
        if (videoTrack) {
          videoTrack.onended = () => {
            console.warn('Camera stream ended unexpectedly. Retrying in 3s...');
            // Wait before trying to reconnect to avoid spamming
            retryTimeout = setTimeout(() => {
              if (active) setRetryTrigger((prev) => prev + 1);
            }, 3000);
          };
        }

        streamRef.current = stream;
        if (videoRef.current) {
          videoRef.current.srcObject = stream;
        }
        setError(null); // Clear errors on successful connection
      } catch (err) {
        if (active) {
          setError(`Camera error: ${err.message}. Retrying...`);
          retryTimeout = setTimeout(() => {
            setRetryTrigger((prev) => prev + 1);
          }, 5000);
        }
      }
    };

    startCamera();

    return () => {
      active = false;
      clearTimeout(retryTimeout);
      if (streamRef.current) {
        streamRef.current.getTracks().forEach((t) => t.stop());
        streamRef.current = null;
      }
    };
  }, [retryTrigger]);

  return (
    <div className="camera-container">
      {error && (
      <div className="camera-retry-status">
        {error}
      </div>
      )}
      <video
        ref={videoRef}
        autoPlay
        className="camera-video"
        muted
        playsInline
      />
    </div>
  );
}

export default Home;
