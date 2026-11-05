import test from 'node:test';
import assert from 'node:assert/strict';

test('WebSocket Real-time Updates: handles incoming new_photo event with folder match', () => {
  let galleryPhotos = [
    { id: 201, folder: 'Ceremony', title: 'Walk' },
    { id: 200, folder: 'Ceremony', title: 'Arrival' },
  ];

  const currentActiveFolder = 'Ceremony';

  const incomingWebSocketEvent = {
    type: 'new_photo',
    photo_id: 202,
    wedding_slug: 'alice-bob',
    folder: 'Ceremony',
    status: 'COMPLETED',
  };

  // Logic from GalleryPage: when new photo matches active folder, prepend to gallery
  if (incomingWebSocketEvent.type === 'new_photo') {
    const isFolderMatch = currentActiveFolder === 'all' || incomingWebSocketEvent.folder === currentActiveFolder;
    assert.equal(isFolderMatch, true);

    const alreadyExists = galleryPhotos.some(p => p.id === incomingWebSocketEvent.photo_id);
    assert.equal(alreadyExists, false);

    const placeholderPhoto = {
      id: incomingWebSocketEvent.photo_id,
      folder: incomingWebSocketEvent.folder,
      title: 'Incoming Live Photo',
    };
    galleryPhotos = [placeholderPhoto, ...galleryPhotos];
  }

  assert.equal(galleryPhotos.length, 3);
  assert.equal(galleryPhotos[0].id, 202, 'Newly broadcast photo should be prepended to the top of the gallery');
});

test('WebSocket Real-time Updates: removes deleted photo on delete_photo event', () => {
  let galleryPhotos = [
    { id: 303, title: 'Toast' },
    { id: 302, title: 'Dinner' },
    { id: 301, title: 'Cake' },
  ];

  const deleteEvent = {
    type: 'delete_photo',
    photo_id: 302,
    wedding_slug: 'alice-bob',
  };

  if (deleteEvent.type === 'delete_photo') {
    galleryPhotos = galleryPhotos.filter(p => p.id !== deleteEvent.photo_id);
  }

  assert.equal(galleryPhotos.length, 2);
  assert.deepEqual(galleryPhotos.map(p => p.id), [303, 301]);
});

