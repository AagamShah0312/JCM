"""
Enterprise test suite for JCM (spec §61): permission, document-access,
hearing lifecycle, audit, case status, AI retrieval filtering, security.

Run: python manage.py test tests.test_enterprise
"""
from datetime import date, timedelta

from django.test import TestCase
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
