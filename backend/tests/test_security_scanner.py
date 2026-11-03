import unittest

from services.pr_poller import _format_security_description
from services.security_scanner import scan_with_grep


class SSRFGrepScannerTests(unittest.TestCase):
    def _ssrf_findings(self, code: str):
        return [
            finding
            for finding in scan_with_grep({"/src/example.ts": code})
            if finding.owasp == "A10:Server-Side Request Forgery"
        ]

    def test_validation_error_message_is_not_ssrf(self):
        findings = self._ssrf_findings(
            "throw new HttpErrors.BadRequest(`id in req.business_unit.coop_officers has duplicate`)"
        )

        self.assertEqual(findings, [])

    def test_user_controlled_url_to_axios_sink_is_ssrf(self):
        findings = self._ssrf_findings("await axios.get(req.query.userUrl)")

        self.assertEqual(len(findings), 1)
        finding = findings[0]
        self.assertEqual(finding.severity, "HIGH")
        self.assertEqual(finding.source_evidence, "req.query.userUrl")
        self.assertEqual(finding.sink_evidence, "axios.get (...)")
        self.assertEqual(finding.call_path, "req.query.userUrl -> axios.get (...)")

        description = _format_security_description(finding)
        self.assertIn("Source: `req.query.userUrl`", description)
        self.assertIn("Sink: `axios.get (...)`", description)
        self.assertIn("Call path: `req.query.userUrl -> axios.get (...)`", description)

    def test_allowlisted_target_is_not_high_ssrf(self):
        findings = self._ssrf_findings(
            "await axios.get(validateAllowedUrl(req.query.userUrl))"
        )

        self.assertEqual(findings, [])
