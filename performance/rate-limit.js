
import http from 'k6/http';
import { check } from 'k6';
import { Counter } from 'k6/metrics';

const blocked = new Counter('rate_limit_429');

export const options = {
  vus: 10,
  duration: '8s',
  thresholds: {
    rate_limit_429: ['count>0'],
  },
};

const BASE_URL =
  __ENV.BASE_URL || 'http://127.0.0.1:8000';

export default function () {
  const response = http.get(
    `${BASE_URL}/api/v1/documents`,
    {
      responseCallback: http.expectedStatuses(200, 429),
    }
  );

  check(response, {
    'Respuesta 200 o 429': (r) =>
      r.status === 200 || r.status === 429,
  });

  if (response.status === 429) {
    blocked.add(1);
  }
}
