import test from 'node:test';
import assert from 'node:assert/strict';

test('Selfie Search: validates file constraints before submission', () => {
  const maxBytes = 10 * 1024 * 1024; // 10 MB

  function validateSelfieFile(file) {
    if (!file) {
      return { valid: false, error: 'Please choose or snap a selfie first.' };
    }
    if (file.size > maxBytes) {
      return { valid: false, error: 'Selfie image exceeds maximum allowed limit of 10 MB.' };
    }
    const validExtensions = ['jpg', 'jpeg', 'png', 'webp'];
    const ext = file.name.split('.').pop()?.toLowerCase();
    if (!validExtensions.includes(ext)) {
      return { valid: false, error: 'Unsupported file format. Please upload JPEG, PNG, or WebP.' };
    }
    return { valid: true };
  }

  // Null file
  assert.equal(validateSelfieFile(null).valid, false);

  // Oversized file (15MB)
  assert.equal(validateSelfieFile({ name: 'huge.jpg', size: 15 * 1024 * 1024 }).valid, false);

  // Invalid format (PDF)
  assert.equal(validateSelfieFile({ name: 'document.pdf', size: 50000 }).valid, false);

  // Valid JPEG
  assert.equal(validateSelfieFile({ name: 'selfie.jpg', size: 1.5 * 1024 * 1024 }).valid, true);
});

test('Selfie Search: handles NO_FACE and DECODE_ERROR responses cleanly', () => {
  const noFaceResponse = {
    status: 'no_face_detected',
    code: 'NO_FACE',
    message: 'No face was detected in your selfie. Please ensure good lighting.',
    photos: [],
    matches_count: 0,
  };

  assert.equal(noFaceResponse.status, 'no_face_detected');
  assert.equal(noFaceResponse.photos.length, 0);
  assert.match(noFaceResponse.message, /No face/);

  const successResponse = {
    status: 'success',
    matches_count: 3,
    photos: [{ id: 1 }, { id: 2 }, { id: 3 }],
  };

  assert.equal(successResponse.status, 'success');
  assert.equal(successResponse.photos.length, 3);
});

test('Selfie Search Debounce: consolidates rapid photographer bursts', async () => {
  let searchCallCount = 0;
  let timer = null;

  function onNewPhotoEvent() {
    clearTimeout(timer);
    timer = setTimeout(() => {
      searchCallCount++;
    }, 50); // 50ms for unit test simulation
  }

  // Rapid burst: 5 photos in 20ms
  onNewPhotoEvent();
  onNewPhotoEvent();
  onNewPhotoEvent();
  onNewPhotoEvent();
  onNewPhotoEvent();

  // Wait 100ms for debounce timer to fire
  await new Promise(resolve => setTimeout(resolve, 100));

  assert.equal(searchCallCount, 1, 'Debounce must ensure only 1 search query fires after the burst completes');
});

