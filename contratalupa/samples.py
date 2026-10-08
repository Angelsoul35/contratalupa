"""A synthetic sample contract for the demo and the tests.

It is deliberately uneven: it contains several standard clauses, a couple with
risky language (unlimited liability, automatic renewal, broad indemnification),
and it is missing some clauses a sound services contract would normally have
(data protection, a dispute-resolution mechanism), so the analyser has something
to find.
"""

from __future__ import annotations

SAMPLE_CONTRACT = """\
MASTER SERVICES AGREEMENT

1. Term. This Agreement commences on the Effective Date and shall automatically
renew for successive one-year periods unless either party gives notice.

2. Payment. The Client shall pay all fees within fifteen (15) days of each
invoice. All amounts are non-refundable.

3. Termination. Either party may terminate this Agreement for material breach
upon thirty (30) days written notice.

4. Liability. The Provider shall bear unlimited liability for any and all
damages arising out of or in connection with this Agreement, without limitation.

5. Indemnification. The Client shall indemnify and hold harmless the Provider
from any and all claims, at the Provider's sole discretion.

6. Confidentiality. Each party shall keep the other party's confidential
information secret and shall not disclose it to any third party.

7. Intellectual Property. All work product and intellectual property created
under this Agreement shall be the exclusive property of the Provider in
perpetuity.

8. Governing Law. This Agreement shall be governed by the laws of the State of
Delaware.
"""
