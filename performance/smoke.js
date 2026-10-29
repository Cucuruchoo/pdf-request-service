
import http from 'k6/http';
import { check, sleep } from 'k6';

export const options = {
  vus: 2,
  duration: '15s',
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
