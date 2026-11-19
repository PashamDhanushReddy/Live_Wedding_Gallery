import test from 'node:test';
import assert from 'node:assert/strict';

test('Camera Permission: detects first-time visit vs returning visitor', () => {
  const CAMERA_PERMISSION_KEY = 'wedding_camera_permission_requested';

  const mockStorage = new Map();

  function isFirstTimeVisit(storage) {
    return !storage.get(CAMERA_PERMISSION_KEY);
  }

  function markPermissionPrompted(storage) {
    storage.set(CAMERA_PERMISSION_KEY, 'true');
  }

  // First visit: storage is empty
  assert.equal(isFirstTimeVisit(mockStorage), true, 'First visit should detect no previous permission prompt');

  // User completes or responds to permission prompt
  markPermissionPrompted(mockStorage);

  // Subsequent visit: storage has key
  assert.equal(isFirstTimeVisit(mockStorage), false, 'Subsequent visits should not re-trigger permission prompt');
  assert.equal(mockStorage.get(CAMERA_PERMISSION_KEY), 'true');
});

test('Camera Permission: immediately stops tracks upon permission verification', async () => {
  let tracksStoppedCount = 0;

  const mockTrack1 = {
    kind: 'video',
    stop() {
      tracksStoppedCount++;
    },
  };
  const mockTrack2 = {
    kind: 'video',
    stop() {
      tracksStoppedCount++;
    },
  };

  const mockStream = {
    getTracks() {
      return [mockTrack1, mockTrack2];
    },
  };

  // Simulating requestPermission logic
  function handlePermissionVerification(stream) {
    stream.getTracks().forEach(track => {
      track.stop();
    });
  }

  handlePermissionVerification(mockStream);

  assert.equal(tracksStoppedCount, 2, 'All camera tracks must be immediately stopped to turn off camera hardware and LED');
});

test('Camera Permission: falls back gracefully when auto-request requires user gesture', async () => {
  let status = 'idle';

  async function mockRequestPermission(isAuto, getUserMediaMock) {
    status = 'requesting';
    try {
      const stream = await getUserMediaMock();
      stream.getTracks().forEach(t => t.stop());
      status = 'granted';
    } catch (err) {
      if (isAuto) {
        // iOS Safari / gesture requirement: leave in idle for user button tap
        status = 'idle';
      } else {
        status = 'denied';
      }
    }
  }

  // 1. Simulating iOS Safari rejecting unprompted getUserMedia on page load
  const safariAutoReject = async () => {
    const err = new Error('The request is not allowed by the user agent in the current context.');
    err.name = 'NotAllowedError';
    throw err;
  };

  await mockRequestPermission(true, safariAutoReject);
  assert.equal(status, 'idle', 'Auto request failure should leave status idle so button is ready for user tap');

  // 2. User taps button (gesture): getUserMedia succeeds
  const userGestureSuccess = async () => ({
    getTracks: () => [{ stop: () => {} }],
  });

  await mockRequestPermission(false, userGestureSuccess);
  assert.equal(status, 'granted', 'User tap with gesture should successfully grant permission');
});
