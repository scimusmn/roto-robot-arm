import React, { useEffect, useRef, useState } from 'react';

const ENV_DEVICE_ID = process.env.GATSBY_CAMERA_DEVICE_ID || '';
const LS_KEY = 'cameraDeviceId';
const vidWidth = 1920;
const vidHeight = 1080;

function Home() {
  const videoRef = useRef(null);
  const streamRef = useRef(null);
  const [error, setError] = useState(null);

  useEffect(() => {
    // Resolve device ID: env var → localStorage → default
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

    let active = true;

    navigator.mediaDevices
      .getUserMedia(constraints)
      .then((stream) => {
        if (!active) {
          stream.getTracks().forEach((t) => t.stop());
          return;
        }
        streamRef.current = stream;
        if (videoRef.current) {
          videoRef.current.srcObject = stream;
        }
      })
      .catch((err) => {
        if (active) setError(err.message);
      });

    return () => {
      active = false;
      if (streamRef.current) {
        streamRef.current.getTracks().forEach((t) => t.stop());
        streamRef.current = null;
      }
    };
  }, []);

  if (error) {
    return (
      <div className="camera-error">
        <h2>Camera error</h2>
        {error}
      </div>
    );
  }

  return (
    // eslint-disable-next-line jsx-a11y/media-has-caption
    <video
      ref={videoRef}
      autoPlay
      className="camera-video"
      muted
      playsInline
    />
  );
}

export default Home;
