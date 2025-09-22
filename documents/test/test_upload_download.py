from unittest.mock import patch
from django.test import TestCase
from django.core.files.uploadedfile import SimpleUploadedFile
from django.contrib.auth.models import User
from documents.models import Company, EntityRef

class UploadDownloadTest(TestCase):
    def setUp(self):
        self.user = User.objects.create_user("tester", password="123")
        self.company = Company.objects.create(legal_name="TestCo")
        self.entity = EntityRef.objects.create(
            company=self.company,
            entity_type="vehicle",
            external_id="veh1"
        )
        self.client.force_login(self.user)

    @patch("core.views.boto3.client")  # Mock de boto3 para no depender de MinIO real
    def test_direct_upload(self, mock_boto):
        mock_s3 = mock_boto.return_value
        mock_s3.upload_fileobj.return_value = None

        file = SimpleUploadedFile(
            "test.pdf",
            b"fake-content",
            content_type="application/pdf"
        )

        resp = self.client.post(
            "/api/documents/direct-upload",
            {
                "company_id": str(self.company.id),
                "entity_type": "vehicle",
                "entity_id": str(self.entity.external_id),
                "file": file,
            }
        )

        self.assertEqual(resp.status_code, 201)
        self.assertIn("document_id", resp.json())
