
import http from 'k6/http';
import { check } from 'k6';
import { Counter } from 'k6/metrics';

const created = new Counter('pdf_created_201');
const limited = new Counter('pdf_limited_429');

export const options = {
  scenarios: {
    upload: {
      executor: 'per-vu-iterations',
      vus: 20,
      iterations: 1,
      maxDuration: '60s',
    },
  },
  thresholds: {
    checks: ['rate==1'],
  },
};

const BASE_URL =
  __ENV.BASE_URL || 'http://127.0.0.1:8000';

// Genera un PDF real, simple y diferente en cada solicitud.
function createPDF(id) {
  let pdf = '%PDF-1.4\n';
  const offsets = [0];

  function addObject(number, content) {
    offsets.push(pdf.length);
    pdf += `${number} 0 obj\n${content}\nendobj\n`;
  }

  addObject(1, '<< /Type /Catalog /Pages 2 0 R >>');
  addObject(2, '<< /Type /Pages /Kids [3 0 R] /Count 1 >>');

  addObject(
    3,
    '<< /Type /Page /Parent 2 0 R ' +
      '/MediaBox [0 0 595 842] ' +
      '/Resources << /Font << /F1 5 0 R >> >> ' +
      '/Contents 4 0 R >>'
  );

  const text =
    `BT\n/F1 12 Tf\n72 720 Td\n` +
    `(Performance test ${id}) Tj\nET\n`;

  addObject(
    4,
    `<< /Length ${text.length} >>\n` +
      `stream\n${text}endstream`
  );

  addObject(
    5,
    '<< /Type /Font /Subtype /Type1 ' +
      '/BaseFont /Helvetica >>'
  );

  const xrefPosition = pdf.length;

  pdf += 'xref\n0 6\n0000000000 65535 f \n';

  for (let i = 1; i < offsets.length; i++) {
    pdf +=
      `${String(offsets[i]).padStart(10, '0')} ` +
      `00000 n \n`;
  }

  pdf +=
    'trailer\n<< /Size 6 /Root 1 0 R >>\n' +
    `startxref\n${xrefPosition}\n%%EOF\n`;

  return pdf;
}

export default function () {
  const uniqueId = `${Date.now()}-${__VU}-${__ITER}`;
  const filename = `k6-test-${uniqueId}.pdf`;
  const pdf = createPDF(uniqueId);

  const response = http.post(
    `${BASE_URL}/api/v1/documents`,
    pdf,
    {
      headers: {
        'Content-Type': 'application/pdf',
        'X-Filename': filename,
      },
      responseCallback: http.expectedStatuses(201, 429),
    }
  );

  created.add(response.status === 201 ? 1 : 0);
  limited.add(response.status === 429 ? 1 : 0);

  check(response, {
    'POST devuelve 201 o 429': (r) =>
      r.status === 201 || r.status === 429,
  });

  if (response.status !== 201 && response.status !== 429) {
    console.error(
      `Error ${response.status}: ${response.body}`
    );
  }
}
