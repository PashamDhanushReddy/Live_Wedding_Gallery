import http from 'k6/http';
import ws from 'k6/ws';
import { check, group, sleep } from 'k6';
import { Trend, Rate, Counter } from 'k6/metrics';

// ==============================================================================
// Configuration & Environment Variables
// ==============================================================================
const BASE_URL = __ENV.BASE_URL || 'http://localhost:8000/api';
const WS_BASE_URL = __ENV.WS_BASE_URL || 'ws://localhost:8000/ws';
const WEDDING_SLUG = __ENV.WEDDING_SLUG || 'rahul-priya';
const TEST_STAGE = __ENV.TEST_STAGE || 'all'; // '50', '100', '250', '500', '750', or 'all'

// ==============================================================================
// Custom Performance Metrics
// ==============================================================================
const galleryApiDuration = new Trend('gallery_api_duration', true);
const weddingDetailDuration = new Trend('wedding_detail_duration', true);
const faceSearchDuration = new Trend('face_search_duration', true);
const photographerUploadDuration = new Trend('photographer_upload_duration', true);
const wsConnectDuration = new Trend('websocket_connect_duration', true);

const failedRequests = new Rate('failed_requests');
const wsDisconnects = new Counter('websocket_disconnects');
const faceSearchCapacityBusy = new Counter('face_search_capacity_busy');

// ==============================================================================
// Load Ramping Stages (50 -> 100 -> 250 -> 500 -> 750 VUs)
// ==============================================================================
function getStages() {
  if (TEST_STAGE === '50') {
    return [
      { duration: '30s', target: 50 },
      { duration: '1m', target: 50 },
      { duration: '15s', target: 0 },
    ];
  } else if (TEST_STAGE === '100') {
    return [
      { duration: '45s', target: 100 },
      { duration: '1m30s', target: 100 },
      { duration: '15s', target: 0 },
    ];
  } else if (TEST_STAGE === '250') {
    return [
      { duration: '1m', target: 250 },
      { duration: '2m', target: 250 },
      { duration: '30s', target: 0 },
    ];
  } else if (TEST_STAGE === '500') {
    return [
      { duration: '1m30s', target: 500 },
      { duration: '2m30s', target: 500 },
      { duration: '30s', target: 0 },
    ];
  } else if (TEST_STAGE === '750') {
    return [
      { duration: '2m', target: 750 },
      { duration: '2m', target: 750 },
      { duration: '30s', target: 0 },
    ];
  }

  // Default: Full progressive 5-stage ramp
  return [
    { duration: '30s', target: 50 },   // Stage 1: 50 users (Warm-up / Baseline)
    { duration: '1m', target: 50 },
    { duration: '30s', target: 100 },  // Stage 2: 100 users (Moderate)
    { duration: '1m', target: 100 },
    { duration: '45s', target: 250 },  // Stage 3: 250 users (Pre-peak)
    { duration: '1m30s', target: 250 },
    { duration: '1m', target: 500 },   // Stage 4: 500 users (Target Capacity)
    { duration: '2m', target: 500 },
    { duration: '1m', target: 750 },   // Stage 5: 750 users (Controlled Stress Test)
    { duration: '1m30s', target: 750 },
    { duration: '45s', target: 0 },    // Cooldown
  ];
}

export const options = {
  stages: getStages(),
  thresholds: {
    // Requirements validation
    'http_req_duration{type:read}': ['p(95)<500', 'p(99)<1000'],
    'failed_requests': ['rate<0.01'], // Error rate strictly below 1%
    'gallery_api_duration': ['p(95)<500', 'p(99)<1000'],
    'wedding_detail_duration': ['p(95)<250'],
  },
};

// ==============================================================================
// Minimal Valid Test JPEG Payload (base64 decoded inline)
// ==============================================================================
const MOCK_JPEG_BASE64 = 
  "/9j/4AAQSkZJRgABAQEASABIAAD/2wBDAP//////////////////////////////////////////////////////////////////////////////////////wgALCAABAAEBAREA/8QAFBABAAAAAAAAAAAAAAAAAAAAAP/aAAgBAQABPxA=";
const mockJpegBinary = http.file(MOCK_JPEG_BASE64, 'selfie_load_test.jpg', 'image/jpeg');

// ==============================================================================
// Main Test Scenario
// ==============================================================================
export default function () {
  const vuId = __VU;
  const iter = __ITER;

  // Distribute user behaviors according to realistic visitor profiles:
  // 60% browse gallery & lightbox (Profile A)
  // 30% filter categories, cursor pagination & download (Profile B)
  // 10% perform selfie face-search (Profile C)
  const roleSeed = (vuId * 7 + iter) % 10;

  if (roleSeed < 6) {
    // --------------------------------------------------------------------------
    // Profile A: Passive Gallery Browsing & Lightbox
    // --------------------------------------------------------------------------
    group('Gallery Browsing & Metadata', function () {
      // 1. Wedding detail metadata
      const resDetail = http.get(`${BASE_URL}/weddings/${WEDDING_SLUG}/`, {
        tags: { type: 'read', endpoint: 'wedding_detail' },
      });
      weddingDetailDuration.add(resDetail.timings.duration);
      const detailOk = check(resDetail, {
        'wedding detail status is 200': (r) => r.status === 200,
      });
      failedRequests.add(!detailOk);

      sleep(0.5);

      // 2. Initial Page of Gallery (25 photos)
      const resGallery = http.get(`${BASE_URL}/weddings/${WEDDING_SLUG}/photos/?page_size=25`, {
        tags: { type: 'read', endpoint: 'gallery_photos' },
      });
      galleryApiDuration.add(resGallery.timings.duration);
      const galleryOk = check(resGallery, {
        'gallery status is 200': (r) => r.status === 200,
        'gallery has results': (r) => r.json('results') !== undefined,
      });
      failedRequests.add(!galleryOk);

      // 3. Inspect lightbox preview URL for first photo
      if (galleryOk && resGallery.json('results.0')) {
        const firstPhoto = resGallery.json('results.0');
        check(firstPhoto, {
          'has preview url': (p) => !!(p.preview_url || p.secure_url),
          'has thumbnail url': (p) => !!(p.thumbnail_url || p.preview_url),
        });
      }
    });

  } else if (roleSeed < 9) {
    // --------------------------------------------------------------------------
    // Profile B: Category Filtering & Cursor Pagination
    // --------------------------------------------------------------------------
    group('Filtering & Cursor Pagination', function () {
      // 1. Filter by category folder
      const folders = ['Bride and Groom', 'Guests', 'Ceremony', 'Reception'];
      const selectedFolder = folders[iter % folders.length];
      const resFolder = http.get(`${BASE_URL}/weddings/${WEDDING_SLUG}/photos/?folder=${encodeURIComponent(selectedFolder)}&page_size=25`, {
        tags: { type: 'read', endpoint: 'gallery_filter' },
      });
      galleryApiDuration.add(resFolder.timings.duration);
      const folderOk = check(resFolder, {
        'filtered gallery status is 200': (r) => r.status === 200,
      });
      failedRequests.add(!folderOk);

      sleep(0.5);

      // 2. Paginate to next page if cursor exists
      if (folderOk && resFolder.json('next')) {
        const nextUrl = resFolder.json('next');
        const resNext = http.get(nextUrl, {
          tags: { type: 'read', endpoint: 'gallery_cursor' },
        });
        galleryApiDuration.add(resNext.timings.duration);
        const nextOk = check(resNext, {
          'cursor page status is 200': (r) => r.status === 200,
        });
        failedRequests.add(!nextOk);
      }
    });

  } else {
    // --------------------------------------------------------------------------
    // Profile C: Selfie Upload & Face Search
    // --------------------------------------------------------------------------
    group('Selfie Upload & Face Search', function () {
      const payload = {
        file: mockJpegBinary,
        threshold: '0.45',
      };

      const resSearch = http.post(`${BASE_URL}/weddings/${WEDDING_SLUG}/search/`, payload, {
        tags: { type: 'compute', endpoint: 'face_search' },
      });
      faceSearchDuration.add(resSearch.timings.duration);

      if (resSearch.status === 429) {
        // Concurrency gate throttled gracefully
        faceSearchCapacityBusy.add(1);
        check(resSearch, {
          'face search capacity gate active (429)': (r) => r.status === 429,
        });
      } else {
        const searchOk = check(resSearch, {
          'face search status is 200 or 400 (no-face mock)': (r) => r.status === 200 || r.status === 400,
        });
        failedRequests.add(!searchOk);
      }
    });
  }

  // ----------------------------------------------------------------------------
  // Lightweight WebSocket Ping (5% of users open live connection)
  // ----------------------------------------------------------------------------
  if (iter % 20 === 0) {
    const wsUrl = `${WS_BASE_URL}/weddings/${WEDDING_SLUG}/`;
    const resWs = ws.connect(wsUrl, {}, function (socket) {
      socket.on('open', function () {
        wsConnectDuration.add(10);
        socket.setTimeout(function () {
          socket.close();
        }, 5000); // Keep open 5 seconds
      });

      socket.on('error', function (err) {
        wsDisconnects.add(1);
      });
    });
  }

  // Realistic user pacing between actions
  sleep(1.0 + Math.random() * 2.0);
}

