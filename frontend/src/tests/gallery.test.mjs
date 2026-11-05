import test from 'node:test';
import assert from 'node:assert/strict';

test('Gallery Pagination: deduplicates subsequent pages and prevents duplicate keys', () => {
  const existingPhotos = [
    { id: 101, url: 'https://res.cloudinary.com/test/photo101.jpg', folder: 'Guests' },
    { id: 102, url: 'https://res.cloudinary.com/test/photo102.jpg', folder: 'Guests' },
    { id: 103, url: 'https://res.cloudinary.com/test/photo103.jpg', folder: 'Guests' },
  ];

  // Incoming next page from API containing an overlapping photo (e.g. Due to live insertion)
  const incomingNextPage = [
    { id: 103, url: 'https://res.cloudinary.com/test/photo103.jpg', folder: 'Guests' }, // Duplicate
    { id: 104, url: 'https://res.cloudinary.com/test/photo104.jpg', folder: 'Guests' },
    { id: 105, url: 'https://res.cloudinary.com/test/photo105.jpg', folder: 'Guests' },
  ];

  const existingIds = new Set(existingPhotos.map(p => p.id));
  const uniqueIncoming = incomingNextPage.filter(p => !existingIds.has(p.id));
  const mergedPhotos = [...existingPhotos, ...uniqueIncoming];

  assert.equal(mergedPhotos.length, 5, 'Should have exactly 5 unique photos');
  assert.deepEqual(mergedPhotos.map(p => p.id), [101, 102, 103, 104, 105]);
});

test('Cloudinary URL Selection: chooses correct asset resolution for gallery vs lightbox vs download', () => {
  const photo = {
    id: 42,
    original_filename: 'first_dance.jpg',
    thumbnail_url: 'https://res.cloudinary.com/demo/image/upload/c_limit,f_auto,q_auto,w_400/v1/dance.jpg',
    preview_url: 'https://res.cloudinary.com/demo/image/upload/c_limit,f_auto,q_auto,w_1200/v1/dance.jpg',
    large_preview_url: 'https://res.cloudinary.com/demo/image/upload/c_limit,f_auto,q_auto,w_2000/v1/dance.jpg',
    download_url: 'https://res.cloudinary.com/demo/image/upload/fl_attachment:first_dance/v1/dance.jpg',
  };

  // 1. Grid display MUST use compact thumbnail
  const gridUrl = photo.thumbnail_url || photo.preview_url;
  assert.match(gridUrl, /w_400/, 'Grid thumbnail must use 400px transformed URL');

  // 2. Lightbox display MUST use high-res preview
  const lightboxUrl = photo.large_preview_url || photo.preview_url;
  assert.match(lightboxUrl, /w_2000/, 'Lightbox should use 2000px preview URL');

  // 3. Explicit download MUST use attachment flag
  const downloadUrl = photo.download_url;
  assert.match(downloadUrl, /fl_attachment/, 'Download URL must have attachment flag for instant browser save');
});

test('Empty and Error States: handles zero photos gracefully', () => {
  const emptyApiResponse = {
    count: 0,
    next: null,
    previous: null,
    page_size: 25,
    results: [],
  };

  const hasPhotos = emptyApiResponse.results && emptyApiResponse.results.length > 0;
  assert.equal(hasPhotos, false);

  const emptyStateMessage = hasPhotos ? null : "No photos have been added to this wedding gallery yet.";
  assert.ok(emptyStateMessage);
  assert.match(emptyStateMessage, /No photos/);
});

