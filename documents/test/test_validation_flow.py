import uuid
from django.contrib.auth.models import User
from django.test import TestCase
from documents.models import Company, CompanyMembership, EntityRef, Document
from documents.services import create_document_with_optional_flow, approve_document, reject_document

class ValidationFlowTest(TestCase):
    def setUp(self):
        self.company = Company.objects.create(legal_name="Acme")
        self.u1 = User.objects.create_user(username="l1", password="x")
        self.u2 = User.objects.create_user(username="l2", password="x")
        self.u3 = User.objects.create_user(username="l3", password="x")
        self.cu1 = CompanyMembership.objects.create(company=self.company, user=self.u1, approval_level=1)
        self.cu2 = CompanyMembership.objects.create(company=self.company, user=self.u2, approval_level=2)
        self.cu3 = CompanyMembership.objects.create(company=self.company, user=self.u3, approval_level=3)
        self.entity = EntityRef.objects.create(
            company=self.company, entity_type="vehicle", external_id=uuid.uuid4()
        )

    def _create_doc(self):
        doc = create_document_with_optional_flow(
            creator=self.u1, company=self.company, entity=self.entity,
            doc_payload={
                "name": "soat.pdf", "mime_type": "application/pdf",
                "size_bytes": 100, "bucket_key": "k/acme/soat.pdf"
            },
            flow_payload={
                "enabled": True,
                "steps": [
                    {"order": 1, "approver_user_id": str(self.u1.id)},
                    {"order": 2, "approver_user_id": str(self.u2.id)},
                    {"order": 3, "approver_user_id": str(self.u3.id)},
                ]
            }
        )
        return doc

    def test_highest_order_approves_all(self):
        doc = self._create_doc()
        self.assertEqual(doc.validation_status, "P")
        approve_document(document=doc, actor_user=self.u3, reason="ok top")
        doc.refresh_from_db()
        self.assertEqual(doc.validation_status, "A")

    def test_middle_order_keeps_pending(self):
        doc = self._create_doc()
        approve_document(document=doc, actor_user=self.u2, reason="ok mid")
        doc.refresh_from_db()
        self.assertEqual(doc.validation_status, "P")  # aún falta L3

    def test_reject_is_terminal(self):
        doc = self._create_doc()
        reject_document(document=doc, actor_user=self.u1, reason="ilegible")
        doc.refresh_from_db()
        self.assertEqual(doc.validation_status, "R")
