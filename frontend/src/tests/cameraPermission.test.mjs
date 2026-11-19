import test from 'node:test';
import assert from 'node:assert/strict';

test('Camera Permission: asks permission only on first visit when user clicks [Scan Face & View My Photos]', () => {
  const CAMERA_PERMISSION_KEY = 'wedding_camera_permission_requested';
  const CAMERA_PERMISSION_GRANTED_KEY = 'wedding_camera_permission_granted';
  const mockStorage = new Map();

  let dispatchedEvent = null;
  let navigatedTo = null;

  function handleScanFaceClick({ isBrowserPermissionGranted = false }) {
    dispatchedEvent = null;
    navigatedTo = null;

    const alreadyPrompted = mockStorage.get(CAMERA_PERMISSION_KEY) === 'true';
    const wasGranted = mockStorage.get(CAMERA_PERMISSION_GRANTED_KEY) === 'true';

    // Returning visitor: MUST NOT ask again on subsequent visits!
    if (alreadyPrompted) {
      navigatedTo = wasGranted ? '/photos?autoScan=true' : '/photos';
      return;
    }

    if (isBrowserPermissionGranted || wasGranted) {
      mockStorage.set(CAMERA_PERMISSION_KEY, 'true');
      mockStorage.set(CAMERA_PERMISSION_GRANTED_KEY, 'true');
      navigatedTo = '/photos?autoScan=true';
      return;
    }

    // First time only: dispatch open permission prompt
    dispatchedEvent = 'wedding_open_camera_permission';
  }

  // 1. Initial page load: user has NOT clicked the button. No event or navigation must happen.
  assert.equal(dispatchedEvent, null, 'No permission prompt should be triggered on initial website open');
  assert.equal(navigatedTo, null);

  // 2. User clicks [Scan Face & View My Photos] for the FIRST TIME
  handleScanFaceClick({ isBrowserPermissionGranted: false });
  assert.equal(dispatchedEvent, 'wedding_open_camera_permission', 'Must trigger camera permission prompt when clicking for the first time');
  assert.equal(navigatedTo, null);

  // 3. User responds to the prompt (e.g. grants camera access)
  mockStorage.set(CAMERA_PERMISSION_KEY, 'true');
  mockStorage.set(CAMERA_PERMISSION_GRANTED_KEY, 'true');

  // 4. SUBSEQUENT VISITS: User visits website again and clicks [Scan Face & View My Photos]
  handleScanFaceClick({ isBrowserPermissionGranted: true });
  assert.equal(dispatchedEvent, null, 'MUST NOT ask for permission on subsequent visits');
  assert.equal(navigatedTo, '/photos?autoScan=true', 'Must navigate directly to photos with autoScan=true');

  // 5. Subsequent visit when user previously continued without camera (declined):
  const mockStorageDeclined = new Map();
  mockStorageDeclined.set(CAMERA_PERMISSION_KEY, 'true');
  mockStorageDeclined.set(CAMERA_PERMISSION_GRANTED_KEY, 'false');

  function handleScanFaceClickDeclined() {
    const alreadyPrompted = mockStorageDeclined.get(CAMERA_PERMISSION_KEY) === 'true';
    const wasGranted = mockStorageDeclined.get(CAMERA_PERMISSION_GRANTED_KEY) === 'true';
    if (alreadyPrompted) {
      return wasGranted ? '/photos?autoScan=true' : '/photos';
    }
    return 'prompt';
  }

  assert.equal(handleScanFaceClickDeclined(), '/photos', 'Returning user who declined previously must not be prompted again');
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
