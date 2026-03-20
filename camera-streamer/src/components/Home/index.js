import React, { useEffect, useRef, useState } from 'react';

const ENV_DEVICE_ID = process.env.GATSBY_CAMERA_DEVICE_ID || '';
const LS_KEY = 'cameraDeviceId';

function Home() {
  const videoRef = useRef(null);
  const streamRef = useRef(null);
  const [error, setError] = useState(null);

  useEffect(() => {
    // Resolve device ID: env var → localStorage → default
    const deviceId = ENV_DEVICE_ID || localStorage.getItem(LS_KEY) || undefined;

    const constraints = {
      video: deviceId
        ? { deviceId: { exact: deviceId }, width: { ideal: 1920 }, height: { ideal: 1080 } }
        : { width: { ideal: 1920 }, height: { ideal: 1080 } },
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
      <div style={{
        alignItems: 'center',
        background: '#000',
        color: '#f55',
        display: 'flex',
        flexDirection: 'column',
        height: '100vh',
        justifyContent: 'center',
        width: '100vw',
      }}
      >
        <p style={{ fontSize: '1.2rem', margin: 0 }}>Camera error</p>
        <p style={{ color: '#aaa', fontSize: '0.85rem', marginTop: '0.5rem' }}>{error}</p>
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
