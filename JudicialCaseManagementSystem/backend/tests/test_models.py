from django.test import TestCase
from django.utils import timezone
from django.core.files.uploadedfile import SimpleUploadedFile
from rest_framework.test import APITestCase
from rest_framework import status
from datetime import timedelta


class ModelsSmokeTest(TestCase):
    def setUp(self):
        from apps.authentication.models import User
        from apps.cases.models import Case

        self.admin = User.objects.create_superuser(username='admintest', email='admintest@example.com', password='AdminTest123!')
        self.lawyer = User.objects.create_user(username='lawyertest', email='lawyertest@example.com', password='LawyerTest123!')

        self.case = Case.objects.create(
            case_number='TEST-0001',
            title='Test Case',
            description='This is a test case',
            court_name='Test Court',
            case_type='Civil',
            filing_date=timezone.now().date(),
            status='pending',
            plaintiff_name='Alice',
            defendant_name='Bob',
            created_by=self.admin,
            assigned_lawyer=self.lawyer
        )

    def test_case_creation(self):
        self.assertEqual(self.case.case_number, 'TEST-0001')
        self.assertEqual(self.case.created_by.email, 'admintest@example.com')
        self.assertEqual(self.case.assigned_lawyer.email, 'lawyertest@example.com')


class JudicialWorkflowAPITest(APITestCase):
    def setUp(self):
        from apps.authentication.models import User
        from apps.cases.models import Case

        self.admin = User.objects.create_superuser(
            username='adminapi',
            email='adminapi@example.com',
            password='AdminTest123!',
            role='admin',
        )
        self.judge = User.objects.create_user(
            username='judgeapi',
            email='judgeapi@example.com',
            password='JudgeTest123!',
            role='judge',
            professional_id='J-100',
        )
        self.lawyer = User.objects.create_user(
            username='lawyerapi',
            email='lawyerapi@example.com',
            password='LawyerTest123!',
            role='lawyer',
            professional_id='L-100',
        )
        self.guest = User.objects.create_user(
            username='guestapi',
            email='guestapi@example.com',
            password='GuestTest123!',
            role='guest',
        )
        self.case = Case.objects.create(
            case_number='API-0001',
            title='API Test Case',
            description='Case description',
            court_name='Test Court',
            case_type='Civil',
            filing_date=timezone.now().date(),
            next_hearing_date=timezone.now().date() + timedelta(days=5),
            status='pending',
            plaintiff_name='Plaintiff',
            defendant_name='Defendant',
            created_by=self.admin,
            assigned_judge=self.judge,
            assigned_lawyer=self.lawyer,
        )

    def test_judge_can_create_case_and_admin_only_can_delete(self):
        self.client.force_authenticate(self.judge)
        response = self.client.post('/api/cases/', {
            'case_number': 'JUDGE-0001',
            'title': 'Judge Created',
            'description': 'Created by judge',
            'court_name': 'Test Court',
            'case_type': 'Civil',
            'filing_date': timezone.now().date().isoformat(),
            'next_hearing_date': (timezone.now().date() + timedelta(days=10)).isoformat(),
            'status': 'PENDING',
            'plaintiff_name': 'A',
            'defendant_name': 'B',
            'assigned_judge': str(self.judge.id),
            'assigned_lawyer': str(self.lawyer.id),
            'public_interest_link': 'https://youtube.com/live/example',
        }, format='json')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

        delete_response = self.client.delete(f"/api/cases/{response.data['id']}/")
        self.assertEqual(delete_response.status_code, status.HTTP_403_FORBIDDEN)

        self.client.force_authenticate(self.admin)
        admin_delete = self.client.delete(f"/api/cases/{response.data['id']}/")
        # Soft-delete: cases are archived, not hard-deleted (spec §56)
        self.assertEqual(admin_delete.status_code, status.HTTP_200_OK)
        from apps.cases.models import Case
        self.assertTrue(Case.objects.get(case_number='JUDGE-0001').is_archived)

    def test_judge_updates_hearing_with_document_extraction(self):
        self.client.force_authenticate(self.judge)
        upload = SimpleUploadedFile('statement.txt', b'This is a witness statement.', content_type='text/plain')
        response = self.client.post(f'/api/cases/{self.case.id}/update_hearing/', {
            'next_hearing_date': (timezone.now().date() + timedelta(days=12)).isoformat(),
            'files': [upload],
            'document_types': ['statement'],
            'descriptions': ['Hearing statement'],
        }, format='multipart')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['documents_uploaded'], 1)
        document = self.case.documents.get(document_type='statement')
        self.assertIn('witness statement', document.extraction.extracted_text)

    def test_admin_imports_staff_csv_and_promotes_user(self):
        self.client.force_authenticate(self.admin)
        csv_file = SimpleUploadedFile(
            'Judge.csv',
            b'id,email,first_name,last_name\nJ-200,newjudge@example.com,New,Judge\n',
            content_type='text/csv',
        )
        response = self.client.post('/api/auth/users/import_staff_csv/', {
            'role': 'judge',
            'file': csv_file,
        }, format='multipart')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['created'], 1)

        promote = self.client.post(f'/api/auth/users/{self.lawyer.id}/promote_demote/', {
            'role': 'judge',
            'professional_id': 'J-300',
        }, format='json')
        self.assertEqual(promote.status_code, status.HTTP_200_OK)
        self.lawyer.refresh_from_db()
        self.assertEqual(self.lawyer.role, 'judge')

    def test_guest_can_view_but_not_modify_cases(self):
        # Guests can only see cases explicitly marked public (spec §24/§25).
        from apps.cases.models import Case
        Case.objects.filter(id=self.case.id).update(is_public=True)
        self.case.refresh_from_db()

        self.client.force_authenticate(self.guest)
        list_response = self.client.get('/api/cases/')
        self.assertEqual(list_response.status_code, status.HTTP_200_OK)

        patch_response = self.client.patch(f'/api/cases/{self.case.id}/', {'title': 'Changed'}, format='json')
        self.assertEqual(patch_response.status_code, status.HTTP_403_FORBIDDEN)

        # A guest cannot even discover a non-public case (information hiding).
        from apps.cases.models import Case
        Case.objects.filter(id=self.case.id).update(is_public=False)
        hidden = self.client.get(f'/api/cases/{self.case.id}/')
        self.assertEqual(hidden.status_code, status.HTTP_404_NOT_FOUND)
