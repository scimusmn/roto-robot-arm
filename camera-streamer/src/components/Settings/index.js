import React, { useEffect, useState } from 'react';
import { navigate } from 'gatsby';

const ENV_DEVICE_ID = process.env.GATSBY_CAMERA_DEVICE_ID || '';
const LS_KEY = 'cameraDeviceId';

function Settings() {
  const [devices, setDevices] = useState([]);
  const [selected, setSelected] = useState('');
  const [permissionGranted, setPermissionGranted] = useState(false);

  // We need to call getUserMedia once to unlock the real device labels;
  // without it browsers return empty strings for device labels.
  useEffect(() => {
    navigator.mediaDevices
      .getUserMedia({ video: true, audio: false })
      .then((stream) => {
        stream.getTracks().forEach((t) => t.stop());
        setPermissionGranted(true);
      })
      .catch(() => setPermissionGranted(true)); // still try to list devices
  }, []);

  useEffect(() => {
    if (!permissionGranted) return;

    navigator.mediaDevices
      .enumerateDevices()
      .then((allDevices) => {
        const videoDevices = allDevices.filter((d) => d.kind === 'videoinput');
        setDevices(videoDevices);
        // Pre-select current active device
        const current = ENV_DEVICE_ID || localStorage.getItem(LS_KEY) || '';
        setSelected(current);
      });
  }, [permissionGranted]);

  function handleSelect(deviceId) {
    localStorage.setItem(LS_KEY, deviceId);
    navigate('/');
  }

  return (
    <div className="settings-page">
      <h1>Camera Settings</h1>

      {ENV_DEVICE_ID && (
        <div className="env-notice">
          <strong>GATSBY_CAMERA_DEVICE_ID</strong>
          {' '}
          is set via environment variable and will override any selection below until unset.
          <span className="device-id">{ENV_DEVICE_ID}</span>
        </div>
      )}

      {devices.length === 0 ? (
        <p>No video devices found, or camera permission was denied.</p>
      ) : (
        <ul className="device-list">
          {devices.map((device, i) => (
            <li key={device.deviceId} className="device-item">
              <button
                type="button"
                className={selected === device.deviceId ? 'active' : ''}
                onClick={() => handleSelect(device.deviceId)}
              >
                {device.label || `Camera ${i + 1}`}
                <span className="device-id">{device.deviceId}</span>
              </button>
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}

export default Settings;
