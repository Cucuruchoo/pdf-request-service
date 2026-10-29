
import http from 'k6/http';
import { check, sleep } from 'k6';

export const options = {
  vus: 10,
  duration: '60s',

  thresholds: {
    http_req_failed: ['rate<0.01'],
    http_req_duration: ['p(95)<500'],
    checks: ['rate>0.99'],
  },
};

const BASE_URL =
  __ENV.BASE_URL || 'http://127.0.0.1:8000';

export default function () {
  const response = http.get(
    `${BASE_URL}/api/v1/documents`
  );

  check(response, {
    'GET devuelve 200': (r) => r.status === 200,
  });

  sleep(1);
}
