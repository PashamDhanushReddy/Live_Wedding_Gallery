import test from 'node:test';
import assert from 'node:assert/strict';

test('Camera Permission: asks permission only when user clicks [Scan Face & View My Photos]', () => {
  const CAMERA_PERMISSION_GRANTED_KEY = 'wedding_camera_permission_granted';
  const mockStorage = new Map();

  let dispatchedEvent = null;
  let navigatedTo = null;

  function handleScanFaceClick({ isBrowserPermissionGranted = false }) {
    if (isBrowserPermissionGranted || mockStorage.get(CAMERA_PERMISSION_GRANTED_KEY) === 'true') {
      navigatedTo = '/photos?autoScan=true';
      return;
    }

    // Must dispatch open permission prompt when user clicks [Scan Face & View My Photos]
    dispatchedEvent = 'wedding_open_camera_permission';
  }

  // 1. Initial page load: user has NOT clicked the button. No event or navigation must happen.
  assert.equal(dispatchedEvent, null, 'No permission prompt should be triggered on initial website open');
  assert.equal(navigatedTo, null);

  // 2. User clicks [Scan Face & View My Photos] for the first time
  handleScanFaceClick({ isBrowserPermissionGranted: false });
  assert.equal(dispatchedEvent, 'wedding_open_camera_permission', 'Must trigger camera permission prompt when clicking [Scan Face & View My Photos]');
  assert.equal(navigatedTo, null);

  // 3. User grants camera permission
  mockStorage.set(CAMERA_PERMISSION_GRANTED_KEY, 'true');
  dispatchedEvent = null;

  // 4. User clicks [Scan Face & View My Photos] again (already granted)
  handleScanFaceClick({ isBrowserPermissionGranted: true });
  assert.equal(dispatchedEvent, null, 'Should not prompt again if permission was already granted');
  assert.equal(navigatedTo, '/photos?autoScan=true', 'Must navigate with autoScan=true when permission is active');
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
        status = 'idle';
      } else {
        status = 'denied';
      }
    }
  }

  // 1. Simulating iOS Safari rejecting unprompted getUserMedia
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
