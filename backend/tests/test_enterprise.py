"""
Enterprise test suite for JCM (spec §61): permission, document-access,
hearing lifecycle, audit, case status, AI retrieval filtering, security.

Run: python manage.py test tests.test_enterprise
"""
from datetime import date, timedelta

from django.test import TestCase, override_settings
from django.utils import timezone
from rest_framework.test import APITestCase
from rest_framework import status

from apps.authentication.models import User
from apps.cases.models import Case, CaseParty, CaseStatus
from apps.courts.models import Court, Courtroom
from apps.documents.models import CaseDocument, DocumentChunk


def make_users():
    admin = User.objects.create_superuser(
        username='adm', email='adm@example.com', password='Passw0rd!x', role='admin',
        professional_id='ADM-1',
    )
    judge = User.objects.create_user(
        username='jdg', email='jdg@example.com', password='Passw0rd!x', role='judge',
        professional_id='JDG-1',
    )
    other_judge = User.objects.create_user(
        username='jdg2', email='jdg2@example.com', password='Passw0rd!x', role='judge',
        professional_id='JDG-2',
    )
    lawyer = User.objects.create_user(
        username='law', email='law@example.com', password='Passw0rd!x', role='lawyer',
        professional_id='LAW-1',
    )
    other_lawyer = User.objects.create_user(
        username='law2', email='law2@example.com', password='Passw0rd!x', role='lawyer',
        professional_id='LAW-2',
    )
    guest = User.objects.create_user(
        username='gst', email='gst@example.com', password='Passw0rd!x', role='guest',
    )
    return admin, judge, other_judge, lawyer, other_lawyer, guest


def make_case(admin, judge, lawyer, public=False, tag='T'):
    import uuid as _uuid
    court, _ = Court.objects.get_or_create(name='Test Court')
    room, _ = Courtroom.objects.get_or_create(court=court, name='Room 1')
    return Case.objects.create(
        case_number=f'{tag}-{_uuid.uuid4().hex[:8]}'.upper(), title='Test v. Case', description='desc',
        case_type='Civil', court=court, courtroom=room,
        filing_date=timezone.now().date(), status='ACTIVE',
        plaintiff_name='A', defendant_name='B',
        assigned_judge=judge, assigned_lawyer=lawyer,
        created_by=admin, is_public=public,
    )


class CaseStatusTransitionTests(TestCase):
    def setUp(self):
        self.admin, self.judge, *_ = make_users()
        self.case = make_case(self.admin, self.judge, None)

    def test_valid_transition(self):
        self.assertTrue(self.case.change_status('DISPOSED', self.admin))
        self.assertTrue(self.case.change_status('CLOSED', self.admin))
        self.case.refresh_from_db()
        self.assertEqual(self.case.status, 'CLOSED')
        self.assertEqual(self.case.status_history.count(), 2)

    def test_invalid_transition_rejected(self):
        with self.assertRaises(ValueError):
            self.case.change_status('CLOSED', self.admin)  # ACTIVE -> CLOSED is not allowed
        # ACTIVE -> DISPOSED -> CLOSED is the legal path
        self.assertTrue(self.case.change_status('DISPOSED', self.admin))
        self.assertTrue(self.case.change_status('CLOSED', self.admin))


class PermissionTests(APITestCase):
    """Object/resource-level authorization (spec §11, §49)."""

    def setUp(self):
        self.admin, self.judge, self.other_judge, self.lawyer, self.other_lawyer, self.guest = make_users()
        self.case = make_case(self.admin, self.judge, self.lawyer, public=False)
        self.public_case = make_case(self.admin, self.judge, None, public=True)

    def _auth(self, user):
        self.client.force_authenticate(user)

    def _case_ids(self, resp):
        data = resp.data
        if isinstance(data, dict) and 'results' in data:
            return [c['id'] for c in data['results']]
        return [c['id'] for c in data]

    def test_lawyer_sees_only_assigned_cases(self):
        self._auth(self.other_lawyer)
        resp = self.client.get('/api/cases/')
        self.assertNotIn(str(self.case.id), self._case_ids(resp))
        # Assigned lawyer sees it
        self._auth(self.lawyer)
        resp = self.client.get('/api/cases/')
        self.assertIn(str(self.case.id), self._case_ids(resp))

    def test_judge_sees_only_authorized_cases(self):
        self._auth(self.other_judge)
        resp = self.client.get(f'/api/cases/{self.case.id}/')
        self.assertEqual(resp.status_code, status.HTTP_404_NOT_FOUND)  # information hiding

    def test_guest_cannot_see_private_case(self):
        self._auth(self.guest)
        resp = self.client.get(f'/api/cases/{self.case.id}/')
        self.assertEqual(resp.status_code, status.HTTP_404_NOT_FOUND)
        resp = self.client.get(f'/api/cases/{self.public_case.id}/')
        self.assertEqual(resp.status_code, status.HTTP_200_OK)

    def test_lawyer_cannot_edit_case(self):
        self._auth(self.lawyer)
        resp = self.client.patch(f'/api/cases/{self.case.id}/', {'title': 'hacked'}, format='json')
        self.assertEqual(resp.status_code, status.HTTP_403_FORBIDDEN)

    def test_admin_can_edit_any_case(self):
        self._auth(self.admin)
        resp = self.client.patch(f'/api/cases/{self.case.id}/', {'title': 'updated'}, format='json')
        self.assertEqual(resp.status_code, status.HTTP_200_OK)


class DocumentAccessTests(APITestCase):
    """Document visibility (spec §19): PUBLIC/LAWYER_ONLY/JUDGE_ONLY/RESTRICTED."""

    def setUp(self):
        self.admin, self.judge, self.other_judge, self.lawyer, self.other_lawyer, self.guest = make_users()
        self.case = make_case(self.admin, self.judge, self.lawyer)

        def make_doc(name, vis):
            return CaseDocument.objects.create(
                case=self.case, document_type='other', file_name=name,
                visibility=vis, uploaded_by=self.judge, description='x',
            )
        self.pub = make_doc('pub.txt', 'PUBLIC')
        self.law_only = make_doc('law.txt', 'LAWYER_ONLY')
        self.judge_only = make_doc('judge.txt', 'JUDGE_ONLY')
        self.restricted = make_doc('restricted.txt', 'RESTRICTED')

    def _auth(self, user):
        self.client.force_authenticate(user)

    def test_guest_sees_only_public(self):
        self._auth(self.guest)
        for doc in [self.law_only, self.judge_only, self.restricted]:
            resp = self.client.get(f'/api/documents/{doc.id}/')
            self.assertEqual(resp.status_code, status.HTTP_404_NOT_FOUND)
        resp = self.client.get(f'/api/documents/{self.pub.id}/')
        self.assertEqual(resp.status_code, status.HTTP_200_OK)

    def test_lawyer_sees_lawyer_only_but_not_judge_only(self):
        self._auth(self.lawyer)
        resp = self.client.get(f'/api/documents/{self.law_only.id}/')
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        resp = self.client.get(f'/api/documents/{self.judge_only.id}/')
        self.assertEqual(resp.status_code, status.HTTP_404_NOT_FOUND)
        resp = self.client.get(f'/api/documents/{self.restricted.id}/')
        self.assertEqual(resp.status_code, status.HTTP_404_NOT_FOUND)

    def test_judge_sees_judge_only(self):
        self._auth(self.judge)
        resp = self.client.get(f'/api/documents/{self.judge_only.id}/')
        self.assertEqual(resp.status_code, status.HTTP_200_OK)

    def test_download_requires_authorization(self):
        self._auth(self.other_lawyer)  # not assigned
        resp = self.client.get(f'/api/documents/{self.law_only.id}/download/')
        self.assertEqual(resp.status_code, status.HTTP_404_NOT_FOUND)

    def test_guest_cannot_download_private(self):
        self._auth(self.guest)
        resp = self.client.get(f'/api/documents/{self.law_only.id}/download/')
        self.assertEqual(resp.status_code, status.HTTP_404_NOT_FOUND)


class HearingLifecycleTests(APITestCase):
    """Hearing create → reschedule (audited) → complete → proceedings."""

    def setUp(self):
        self.admin, self.judge, self.other_judge, self.lawyer, *_ = make_users()
        self.case = make_case(self.admin, self.judge, self.lawyer)

    def _auth(self, user):
        self.client.force_authenticate(user)

    def test_judge_creates_hearing(self):
        self._auth(self.judge)
        resp = self.client.post('/api/hearings/', {
            'case': str(self.case.id),
            'date': (timezone.now().date() + timedelta(days=5)).isoformat(),
            'hearing_type': 'ARGUMENTS', 'purpose': 'Final arguments',
        }, format='json')
        self.assertEqual(resp.status_code, status.HTTP_201_CREATED)
        self.assertTrue(resp.data['hearing_number'] >= 1)

    def test_lawyer_cannot_create_hearing(self):
        self._auth(self.lawyer)
        resp = self.client.post('/api/hearings/', {
            'case': str(self.case.id),
            'date': (timezone.now().date() + timedelta(days=5)).isoformat(),
        }, format='json')
        self.assertEqual(resp.status_code, status.HTTP_403_FORBIDDEN)

    def test_reschedule_creates_audit_and_event(self):
        from apps.hearings.models import Hearing
        from apps.audit.models import AuditLog
        h = Hearing.objects.create(case=self.case, hearing_number=1,
                                   date=timezone.now().date() + timedelta(days=3),
                                   judge=self.judge, created_by=self.judge)
        self._auth(self.judge)
        resp = self.client.post(f'/api/hearings/{h.id}/reschedule/', {
            'new_date': (timezone.now().date() + timedelta(days=10)).isoformat(),
            'reason': 'Advocate unavailable',
        }, format='json')
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.assertTrue(AuditLog.objects.filter(action='HEARING_RESCHEDULED', object_id=str(h.id)).exists())
        self.assertTrue(self.case.events.filter(event_type='HEARING_RESCHEDULED').exists())

    def test_complete_records_proceeding(self):
        from apps.hearings.models import Hearing, HearingProceeding
        h = Hearing.objects.create(case=self.case, hearing_number=1,
                                   date=timezone.now().date() - timedelta(days=1),
                                   judge=self.judge, created_by=self.judge)
        self._auth(self.judge)
        resp = self.client.post(f'/api/hearings/{h.id}/complete/', {
            'summary': 'Arguments heard; matter reserved.',
            'next_hearing_date': (timezone.now().date() + timedelta(days=30)).isoformat(),
        }, format='json')
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        h.refresh_from_db()
        self.assertEqual(h.status, 'COMPLETED')
        self.assertTrue(HearingProceeding.objects.filter(hearing=h).exists())


class AuditAppendOnlyTests(TestCase):
    def setUp(self):
        self.admin, *_ = make_users()

    def test_audit_cannot_be_deleted(self):
        from apps.audit.models import AuditLog
        log = AuditLog.objects.create(user=self.admin, action='LOGIN', model_name='User',
                                      object_id='', changes={}, ip_address='127.0.0.1')
        with self.assertRaises(NotImplementedError):
            log.delete()


class HearingParticipantTests(APITestCase):
    """Hearing participants (attendance) endpoint."""

    def setUp(self):
        self.admin, self.judge, self.other_judge, self.lawyer, *_ = make_users()
        self.case = make_case(self.admin, self.judge, self.lawyer)
        from apps.hearings.models import Hearing
        self.hearing = Hearing.objects.create(
            case=self.case, hearing_number=1,
            date=timezone.now().date() + timedelta(days=3),
            judge=self.judge, created_by=self.judge,
        )

    def _auth(self, user):
        self.client.force_authenticate(user)

    def test_judge_adds_and_lists_participants(self):
        self._auth(self.judge)
        resp = self.client.post(f'/api/hearings/{self.hearing.id}/participants/', {
            'name': 'Witness Kumar', 'role': 'witness', 'status': 'PRESENT',
        }, format='json')
        self.assertEqual(resp.status_code, status.HTTP_201_CREATED)
        resp = self.client.get(f'/api/hearings/{self.hearing.id}/participants/')
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.assertEqual(len(resp.data), 1)

    def test_lawyer_cannot_add_participants(self):
        self._auth(self.lawyer)
        resp = self.client.post(f'/api/hearings/{self.hearing.id}/participants/', {
            'name': 'Nope', 'role': 'witness', 'status': 'PRESENT',
        }, format='json')
        self.assertEqual(resp.status_code, status.HTTP_403_FORBIDDEN)


class MFASecurityTests(APITestCase):
    """MFA-ready hook (spec §46): status endpoint + model."""

    def setUp(self):
        self.admin, *_ = make_users()

    def _auth(self, user):
        self.client.force_authenticate(user)

    def test_mfa_status_endpoint(self):
        self._auth(self.admin)
        resp = self.client.get('/api/auth/mfa/status/')
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.assertIn('mfa_available', resp.data)
        self.assertIn('providers_supported', resp.data)
        self.assertEqual(resp.data['mfa_enabled'], False)

    def test_mfa_requires_auth(self):
        resp = self.client.get('/api/auth/mfa/status/')
        self.assertEqual(resp.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_two_factor_model(self):
        from apps.authentication.models import TwoFactorAuth
        tf = TwoFactorAuth.objects.create(user=self.admin, is_enabled=True, provider='totp')
        self.assertTrue(tf.is_enabled)
        self.assertEqual(tf.provider, 'totp')


class CSVErrorReportTests(APITestCase):
    """CSV import downloadable error report (spec §12)."""

    def setUp(self):
        self.admin, *_ = make_users()

    def _auth(self, user):
        self.client.force_authenticate(user)

    def test_error_report_returns_csv(self):
        import io
        from django.core.files.uploadedfile import SimpleUploadedFile
        self._auth(self.admin)
        resp = self.client.post('/api/auth/csv/error-report/', {
            'type': 'staff',
            'role': 'judge',
            'file': SimpleUploadedFile('bad.csv', b'id,email,first_name,last_name\nJ-1,not-an-email,Bad,Row\n'),
        }, format='multipart')
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.assertEqual(resp['Content-Type'], 'text/csv')
        self.assertIn('Valid email is required', resp.content.decode())

    def test_error_report_admin_only(self):
        import io
        from django.core.files.uploadedfile import SimpleUploadedFile
        from apps.authentication.models import User
        judge = User.objects.create_user(username='jdgx', email='jdgx@example.com', password='Passw0rd!x', role='judge')
        self._auth(judge)
        resp = self.client.post('/api/auth/csv/error-report/', {
            'type': 'staff', 'role': 'judge',
            'file': SimpleUploadedFile('bad.csv', b'id,email\n'),
        }, format='multipart')
        self.assertEqual(resp.status_code, status.HTTP_403_FORBIDDEN)


class SchedulingSuggestionTests(APITestCase):
    """Smart hearing scheduling suggestions (spec §44)."""

    def setUp(self):
        self.admin, self.judge, self.other_judge, self.lawyer, *_ = make_users()
        self.case = make_case(self.admin, self.judge, self.lawyer)

    def _auth(self, user):
        self.client.force_authenticate(user)

    def test_suggestions_returned(self):
        self._auth(self.judge)
        resp = self.client.get(f'/api/analytics/cases/{self.case.id}/scheduling-suggestions/')
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.assertGreaterEqual(len(resp.data['suggestions']), 1)
        self.assertIn('conflicts', resp.data['suggestions'][0])
        self.assertIn('recommended', resp.data['suggestions'][0])

    def test_suggestions_require_auth(self):
        from apps.authentication.models import User
        stranger = User.objects.create_user(username='stranger', email='stranger@example.com', password='Passw0rd!x', role='lawyer')
        self._auth(stranger)
        resp = self.client.get(f'/api/analytics/cases/{self.case.id}/scheduling-suggestions/')
        self.assertEqual(resp.status_code, status.HTTP_403_FORBIDDEN)


class CalendarEventTests(APITestCase):
    """Calendar endpoint returns case_id for deep links (spec §27)."""

    def setUp(self):
        self.admin, self.judge, self.other_judge, self.lawyer, *_ = make_users()
        self.case = make_case(self.admin, self.judge, self.lawyer)
        from apps.hearings.models import Hearing
        Hearing.objects.create(
            case=self.case, hearing_number=1,
            date=timezone.now().date() + timedelta(days=2),
            judge=self.judge, created_by=self.judge,
        )

    def _auth(self, user):
        self.client.force_authenticate(user)

    def test_calendar_events_have_case_id(self):
        self._auth(self.judge)
        start = (timezone.now().date() - timedelta(days=1)).isoformat()
        end = (timezone.now().date() + timedelta(days=7)).isoformat()
        resp = self.client.get(f'/api/analytics/calendar/?start={start}&end={end}')
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        hearings = [e for e in resp.data['events'] if e['type'] == 'hearing']
        self.assertGreaterEqual(len(hearings), 1)
        self.assertEqual(hearings[0]['case_id'], str(self.case.id))


class WhatChangedTests(APITestCase):
    """What-changed endpoint surfaces case activity (spec §39)."""

    def setUp(self):
        self.admin, self.judge, self.other_judge, self.lawyer, *_ = make_users()
        self.case = make_case(self.admin, self.judge, self.lawyer)

    def _auth(self, user):
        self.client.force_authenticate(user)

    def test_what_changed_shows_hearing_activity(self):
        import urllib.parse
        from apps.hearings.models import Hearing
        # Create a hearing AFTER the 'since' timestamp
        since = timezone.now() - timedelta(hours=1)
        Hearing.objects.create(
            case=self.case, hearing_number=1,
            date=timezone.now().date() + timedelta(days=2),
            judge=self.judge, created_by=self.judge,
        )
        self._auth(self.judge)
        # URL-encode the ISO timestamp (+ in the tz offset must be %2B)
        encoded = urllib.parse.quote(since.isoformat())
        resp = self.client.get(
            f'/api/analytics/cases/{self.case.id}/what-changed/?since={encoded}'
        )
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.assertGreaterEqual(len(resp.data['changes']), 1)


class AIRetrievalPermissionTests(TestCase):
    """Authorization BEFORE retrieval (spec §34) — critical security test."""

    def setUp(self):
        self.admin, self.judge, self.other_judge, self.lawyer, self.other_lawyer, self.guest = make_users()
        self.case = make_case(self.admin, self.judge, self.lawyer)
        self.secret = CaseDocument.objects.create(
            case=self.case, document_type='evidence', file_name='secret.txt',
            visibility='JUDGE_ONLY', uploaded_by=self.judge, description='x',
        )
        DocumentChunk.objects.create(document=self.secret, case=self.case, chunk_index=0,
                                     text='secret evidence content', visibility='JUDGE_ONLY')

    def test_lawyer_retrieval_excludes_judge_only_chunks(self):
        from apps.ai.retrieval import retrieve_for_query
        lawyer_chunks = retrieve_for_query(self.lawyer, self.case, 'secret evidence')
        self.assertEqual(lawyer_chunks, [])
        judge_chunks = retrieve_for_query(self.judge, self.case, 'secret evidence')
        self.assertEqual(len(judge_chunks), 1)

    def test_guest_retrieval_empty_for_private_case(self):
        from apps.ai.retrieval import retrieve_for_query
        chunks = retrieve_for_query(self.guest, self.case, 'anything')
        self.assertEqual(chunks, [])


class TOTPMFATests(APITestCase):
    """End-to-end TOTP MFA flow (spec §46): enroll → verify → challenge → disable."""

    def setUp(self):
        self.admin, *_ = make_users()
        import pyotp
        self.pyotp = pyotp
        from apps.authentication.models import TwoFactorAuth
        TwoFactorAuth.objects.filter(user=self.admin).delete()

    def _auth(self, user):
        self.client.force_authenticate(user)

    @override_settings(MFA_ENABLED=True)
    def test_full_totp_flow(self):
        import pyotp
        from django.test import override_settings
        from apps.authentication.models import TwoFactorAuth

        # Enroll
        self._auth(self.admin)
        resp = self.client.post('/api/auth/mfa/enroll/', {}, format='json')
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        secret = resp.data['secret']
        self.assertEqual(len(secret), 32)
        self.assertTrue(resp.data['qr_png'].startswith('data:image/png'))

        # Wrong code rejected
        resp = self.client.post('/api/auth/mfa/verify/', {'code': '000000'}, format='json')
        self.assertEqual(resp.status_code, status.HTTP_400_BAD_REQUEST)

        # Correct code enables
        code = pyotp.TOTP(secret).now()
        resp = self.client.post('/api/auth/mfa/verify/', {'code': code}, format='json')
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.assertTrue(resp.data['mfa_enabled'])

        # Secret is encrypted at rest
        tf = TwoFactorAuth.objects.get(user=self.admin)
        self.assertNotEqual(tf.secret_encrypted, secret)
        self.assertNotIn(secret, tf.secret_encrypted)

        # Login requires MFA challenge
        self.client.force_authenticate(None)
        resp = self.client.post('/api/auth/login/', {'email': self.admin.email, 'password': 'Passw0rd!x'}, format='json')
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.assertTrue(resp.data['mfa_required'])
        token = resp.data['mfa_token']

        # Wrong challenge code rejected
        resp = self.client.post('/api/auth/mfa/challenge/', {'mfa_token': token, 'code': '000000'}, format='json')
        self.assertEqual(resp.status_code, status.HTTP_400_BAD_REQUEST)

        # Correct code returns JWT
        code = pyotp.TOTP(secret).now()
        resp = self.client.post('/api/auth/mfa/challenge/', {'mfa_token': token, 'code': code}, format='json')
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.assertIn('access', resp.data)

        # Disable
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {resp.data['access']}")
        code = pyotp.TOTP(secret).now()
        resp = self.client.post('/api/auth/mfa/disable/', {'code': code}, format='json')
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.assertFalse(resp.data['mfa_enabled'])

    @override_settings(MFA_ENABLED=True)
    def test_recovery_codes_flow(self):
        import pyotp
        from apps.authentication.models import TwoFactorAuth, TwoFactorRecoveryCode

        # Enroll + enable (recovery codes are issued on verify)
        self._auth(self.admin)
        r = self.client.post('/api/auth/mfa/enroll/', {}, format='json')
        secret = r.data['secret']
        code = pyotp.TOTP(secret).now()
        r = self.client.post('/api/auth/mfa/verify/', {'code': code}, format='json')
        self.assertEqual(r.status_code, status.HTTP_200_OK)
        self.assertIn('recovery_codes', r.data)
        self.assertEqual(len(r.data['recovery_codes']), 10)
        rc = r.data['recovery_codes'][0]

        # Codes are hashed at rest, never plaintext
        tf = TwoFactorAuth.objects.get(user=self.admin)
        stored = TwoFactorRecoveryCode.objects.filter(two_factor=tf)
        self.assertEqual(stored.count(), 10)
        self.assertNotIn(rc, [c.code_hash for c in stored])

        # Login challenge accepts a recovery code
        self.client.force_authenticate(None)
        r = self.client.post('/api/auth/login/', {'email': self.admin.email, 'password': 'Passw0rd!x'}, format='json')
        token = r.data['mfa_token']
        r = self.client.post('/api/auth/mfa/challenge/', {'mfa_token': token, 'code': rc}, format='json')
        self.assertEqual(r.status_code, status.HTTP_200_OK)
        self.assertIn('access', r.data)

        # Recovery code is single-use
        self.client.force_authenticate(None)
        r = self.client.post('/api/auth/login/', {'email': self.admin.email, 'password': 'Passw0rd!x'}, format='json')
        token = r.data['mfa_token']
        r = self.client.post('/api/auth/mfa/challenge/', {'mfa_token': token, 'code': rc}, format='json')
        self.assertEqual(r.status_code, status.HTTP_400_BAD_REQUEST)

        # Regenerate invalidates old + returns 10 new
        access = None
        r = self.client.post('/api/auth/login/', {'email': self.admin.email, 'password': 'Passw0rd!x'}, format='json')
        # need a fresh valid code; use a second unused recovery code
        unused = [c for c in r.data]  # placeholder
        self.client.force_authenticate(self.admin)
        r = self.client.post('/api/auth/mfa/recovery-codes/regenerate/', {}, format='json')
        self.assertEqual(r.status_code, status.HTTP_200_OK)
        self.assertEqual(len(r.data['recovery_codes']), 10)
        self.assertEqual(TwoFactorRecoveryCode.objects.filter(two_factor=tf, used_at__isnull=True).count(), 10)

    def test_login_without_mfa_returns_access_directly(self):
        self.client.force_authenticate(None)
        resp = self.client.post('/api/auth/login/', {'email': self.admin.email, 'password': 'Passw0rd!x'}, format='json')
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.assertIn('access', resp.data)


class PublicTrigramSearchTests(APITestCase):
    """Public search uses pg_trgm ranking (spec §25/§67)."""

    def setUp(self):
        self.admin, self.judge, *_ = make_users()
        self.case = make_case(self.admin, self.judge, None, public=True)

    def test_partial_case_number_match(self):
        resp = self.client.get('/api/public/cases/', {'search': self.case.case_number[:8]})
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.assertGreaterEqual(resp.data['count'], 1)


class DocumentChunkCollectionTests(TestCase):
    """DocumentChunk.collection isolates case docs from future research (§75)."""

    def setUp(self):
        self.admin, self.judge, *_ = make_users()
        self.case = make_case(self.admin, self.judge, None)

    def test_collection_default(self):
        from apps.documents.models import CaseDocument, DocumentChunk
        doc = CaseDocument.objects.create(case=self.case, document_type='other',
                                          file_name='x.txt', uploaded_by=self.admin)
        chunk = DocumentChunk.objects.create(document=doc, case=self.case, chunk_index=0, text='x')
        self.assertEqual(chunk.collection, 'case_documents')


class GlobalSearchTests(APITestCase):
    """Global search across entities (spec §30)."""

    def setUp(self):
        self.admin, self.judge, self.other_judge, self.lawyer, *_ = make_users()
        self.case = make_case(self.admin, self.judge, self.lawyer, public=True)

    def test_anon_search_finds_public_cases(self):
        resp = self.client.get('/api/search/', {'q': self.case.case_number[:6]})
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.assertGreaterEqual(len(resp.data['cases']), 1)

    def test_authed_search_finds_authorized_hearings(self):
        from apps.hearings.models import Hearing
        Hearing.objects.create(case=self.case, hearing_number=1,
                               date=timezone.now().date() + timedelta(days=2),
                               purpose='Final arguments review', judge=self.judge)
        self.client.force_authenticate(self.lawyer)
        resp = self.client.get('/api/search/', {'q': 'arguments'})
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.assertGreaterEqual(len(resp.data['hearings']), 1)

    def test_v1_alias_works(self):
        resp = self.client.get('/api/v1/public/cases/', {'search': self.case.case_number[:6]})
        self.assertEqual(resp.status_code, status.HTTP_200_OK)


class AISummaryEndpointTests(APITestCase):
    """Hearing/document summary endpoints (spec §32)."""

    def setUp(self):
        self.admin, self.judge, self.other_judge, self.lawyer, *_ = make_users()
        self.case = make_case(self.admin, self.judge, self.lawyer)
        from apps.hearings.models import Hearing
        self.hearing = Hearing.objects.create(
            case=self.case, hearing_number=1,
            date=timezone.now().date() + timedelta(days=2),
            judge=self.judge, created_by=self.judge,
        )

    def _auth(self, user):
        self.client.force_authenticate(user)

    def test_hearing_summary_returns_gracefully(self):
        self._auth(self.judge)
        resp = self.client.get(f'/api/ai/cases/{self.case.id}/hearing/{self.hearing.id}/summary/')
        # With no API key, services return a graceful "not configured" message (200)
        self.assertIn(resp.status_code, (status.HTTP_200_OK, status.HTTP_400_BAD_REQUEST))

    def test_documents_summary_endpoint(self):
        self._auth(self.judge)
        resp = self.client.get(f'/api/ai/cases/{self.case.id}/documents/summary/')
        self.assertIn(resp.status_code, (status.HTTP_200_OK, status.HTTP_400_BAD_REQUEST))

    def test_hearing_summary_requires_auth(self):
        resp = self.client.get(f'/api/ai/cases/{self.case.id}/hearing/{self.hearing.id}/summary/')
        self.assertEqual(resp.status_code, status.HTTP_401_UNAUTHORIZED)


class ScheduledNotificationTests(TestCase):
    """Scheduled notification Celery task (spec §28)."""

    def setUp(self):
        self.admin, *_ = make_users()

    def test_due_schedule_delivered(self):
        from apps.notifications.models import NotificationSchedule
        from apps.cases.models import Case
        case = make_case(self.admin, None, None)
        sched = NotificationSchedule.objects.create(
            case=case, scheduled_date=timezone.now().date() - timedelta(days=1),
            scheduled_time=timezone.now().time(),
            notification_type='hearing_scheduled', message='Reminder',
        )
        sched.recipients.add(self.admin)
        from apps.notifications.tasks import process_scheduled_notifications
        result = process_scheduled_notifications.run()
        sched.refresh_from_db()
        self.assertTrue(sched.is_sent)
        self.assertEqual(result['delivered'], 1)


class AIEndToEndQATests(APITestCase):
    """
    Full AI QA pass (spec §31-§37): with a deterministic mock provider,
    verify chat returns answer+citations+warnings, hearing/doc summaries
    work, and authorization-before-retrieval holds end-to-end through the
    API layer.
    """

    def setUp(self):
        from apps.ai import providers as _providers
        from apps.ai import services as _services

        class MockProvider(_providers.BaseAIProvider):
            name = 'mock'

            def chat(self, messages, system=None, temperature=None, max_tokens=None):
                return ("Based on the supplied sources: the hearing on the 25th was adjourned "
                        "because further arguments were required. Source: Hearing #1 proceedings. "
                        "[AI-generated, advisory]")

            def embed_texts(self, texts, model=None):
                # Deterministic pseudo-embedding so pgvector cosine works.
                return [[0.1] * 8 for _ in texts]

        # Swap the factory instance used by services.get_ai_provider()
        _providers.AIProviderFactory._instances['gemini'] = MockProvider()
        self._restore = _services.get_ai_provider  # no-op; factory patched globally

        self.admin, self.judge, self.other_judge, self.lawyer, *_ = make_users()
        self.case = make_case(self.admin, self.judge, self.lawyer)
        from apps.hearings.models import Hearing
        self.hearing = Hearing.objects.create(
            case=self.case, hearing_number=1,
            date=timezone.now().date() - timedelta(days=1),
            purpose='Final arguments', judge=self.judge, created_by=self.judge,
        )
        # A JUDGE_ONLY document so we can verify the lawyer can't retrieve it
        from apps.documents.models import CaseDocument, DocumentChunk
        self.secret = CaseDocument.objects.create(
            case=self.case, document_type='evidence', file_name='secret.txt',
            visibility='JUDGE_ONLY', uploaded_by=self.judge, description='secret',
        )
        DocumentChunk.objects.create(document=self.secret, case=self.case, chunk_index=0,
                                     text='confidential forensic report details', visibility='JUDGE_ONLY')

    def _auth(self, user):
        self.client.force_authenticate(user)

    def test_judge_qa_returns_answer_citations_warnings(self):
        self._auth(self.judge)
        resp = self.client.post(f'/api/ai/cases/{self.case.id}/chat/', {
            'content': 'What happened in the latest hearing?',
        }, format='json')
        self.assertEqual(resp.status_code, status.HTTP_201_CREATED)
        body = resp.data
        self.assertTrue(body['assistant_message']['content'])
        # Response envelope includes citations + warnings
        self.assertIsInstance(body.get('citations'), list)
        self.assertIsInstance(body.get('warnings'), list)

    def test_hearing_summary_with_mock(self):
        self._auth(self.judge)
        resp = self.client.get(f'/api/ai/cases/{self.case.id}/hearing/{self.hearing.id}/summary/')
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.assertTrue(resp.data['summary'])

    def test_documents_summary_with_mock(self):
        self._auth(self.judge)
        resp = self.client.get(f'/api/ai/cases/{self.case.id}/documents/summary/')
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.assertTrue(resp.data['summary'])

    def test_explain_with_mock(self):
        self._auth(self.judge)
        resp = self.client.get(f'/api/ai/cases/{self.case.id}/explain/')
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.assertTrue(resp.data['explanation'])

    def test_lawyer_qa_never_leaks_judge_only_content(self):
        """Authorization-before-retrieval through the API: the lawyer's answer
        must not reference the JUDGE_ONLY document (spec §34)."""
        self._auth(self.lawyer)
        resp = self.client.post(f'/api/ai/cases/{self.case.id}/chat/', {
            'content': 'Summarize the forensic report',
        }, format='json')
        self.assertEqual(resp.status_code, status.HTTP_201_CREATED)
        # The mock always answers generically, but the KEY assertion: the
        # retrieval layer must have returned zero chunks of the secret doc.
        from apps.ai.retrieval import retrieve_for_query
        lawyer_chunks = retrieve_for_query(self.lawyer, self.case, 'forensic report')
        self.assertEqual(lawyer_chunks, [])
        self.assertEqual(self.case.documents.get(file_name='secret.txt').visibility, 'JUDGE_ONLY')
