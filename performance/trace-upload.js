
import http from 'k6/http';
import { check } from 'k6';
import { createPDF } from './upload.js';

export const options = {
  vus: 1,
  iterations: 1,
  thresholds: {
    checks: ['rate==1'],
  },
};

const BASE_URL =
  __ENV.BASE_URL || 'http://127.0.0.1:8000';

export default function () {
  const requestId =
    __ENV.TRACE_ID || 'evidencia-post-123';

  const uniqueId = Date.now();
  const filename = `trazabilidad-${uniqueId}.pdf`;

  // Cada ejecución genera un PDF diferente.
  const pdf = createPDF(`trace-${uniqueId}`);

  const response = http.post(
    `${BASE_URL}/api/v1/documents`,
    pdf,
    {
      headers: {
        'Content-Type': 'application/pdf',
        'X-Filename': filename,
        'X-Request-ID': requestId,
      },
    }
  );

  check(response, {
    'POST devuelve 201': (r) => r.status === 201,
  });

  console.log(`Request ID: ${requestId}`);
  console.log(`HTTP Status: ${response.status}`);

  if (response.status !== 201) {
    console.error(response.body);
  }
}
