"""
Seed demo data (spec §62): multiple courts, judges, lawyers, cases, parties,
hearings, proceedings, orders, public/private documents, notifications,
audit events. All data is fictional.
"""
import os
from datetime import date, timedelta

from django.core.management.base import BaseCommand
from django.core.files.uploadedfile import SimpleUploadedFile
from django.utils import timezone


class Command(BaseCommand):
    help = 'Seed a rich fictional demo dataset for the JCM platform'

    def handle(self, *args, **options):
        from apps.authentication.models import User
        from apps.courts.models import Court, Courtroom
        from apps.cases.models import (
            Case, CaseParty, CaseLawyer, CaseEvent, CaseStatus, CasePriority,
        )
        from apps.hearings.models import (
            Hearing, HearingProceeding, HearingParticipant, AdjournmentReasonOption,
        )
        from apps.orders.models import Order, OrderVersion
        from apps.documents.models import CaseDocument, DocumentVisibility
        from apps.notifications.models import Notification
        from apps.audit.models import AuditLog, AuditEventType
        from apps.tasks.models import Task

        self.stdout.write('Seeding demo data...')
        today = timezone.now().date()

        # --- Courts & courtrooms ---
        court1, _ = Court.objects.get_or_create(name='City Civil Court, Ahmedabad', defaults={
            'court_type': 'civil', 'city': 'Ahmedabad', 'state': 'Gujarat'})
        court2, _ = Court.objects.get_or_create(name='District & Sessions Court, Ahmedabad', defaults={
            'court_type': 'session', 'city': 'Ahmedabad', 'state': 'Gujarat'})
        room1, _ = Courtroom.objects.get_or_create(court=court1, name='Courtroom 1', defaults={'capacity': 40})
        room2, _ = Courtroom.objects.get_or_create(court=court1, name='Courtroom 2', defaults={'capacity': 25})
        room3, _ = Courtroom.objects.get_or_create(court=court2, name='Courtroom A', defaults={'capacity': 60})

        # --- Adjournment reasons ---
        adj_reasons = [
            ('ADVOCATE_UNAVAILABLE', 'Advocate unavailable'),
            ('WITNESS_UNAVAILABLE', 'Witness unavailable'),
            ('DOCUMENT_PENDING', 'Document pending'),
            ('FURTHER_ARGUMENTS', 'Further arguments required'),
            ('COURT_UNAVAILABLE', 'Court unavailable'),
            ('ADMINISTRATIVE_REASON', 'Administrative reason'),
            ('SETTLEMENT_DISCUSSION', 'Settlement discussion'),
            ('OTHER', 'Other'),
        ]
        for code, label in adj_reasons:
            AdjournmentReasonOption.objects.get_or_create(code=code, defaults={'label': label})

        # --- Users (fictional) ---
        users_data = [
            # email, first, last, role, prof_id
            ('admin@example.com', 'Anita', 'Desai', 'admin', 'ADM-001'),
            ('judge.mehta@example.com', 'Rohan', 'Mehta', 'judge', 'JDG-101'),
            ('judge.patel@example.com', 'Kavita', 'Patel', 'judge', 'JDG-102'),
            ('lawyer.shah@example.com', 'Arjun', 'Shah', 'lawyer', 'BAR-501'),
            ('lawyer.iyer@example.com', 'Meera', 'Iyer', 'lawyer', 'BAR-502'),
            ('lawyer.joshi@example.com', 'Nikhil', 'Joshi', 'lawyer', 'BAR-503'),
            ('guest.public@example.com', 'Guest', 'Public', 'guest', None),
        ]
        users = {}
        for email, fn, ln, role, pid in users_data:
            u, _ = User.objects.get_or_create(email=email, defaults={
                'username': email, 'first_name': fn, 'last_name': ln,
                'role': role, 'professional_id': pid, 'is_verified': True, 'is_active': True,
            })
            if role in ('judge', 'lawyer', 'admin'):
                u.is_verified = True
            u.set_password('Aagam%1234')
            u.save()
            key = role + '_' + (pid.split('-')[-1] if pid else 'public')
            users[key] = u

        admin = users['admin_001']
        judge1 = users['judge_101']
        judge2 = users['judge_102']
        lawyer1 = users['lawyer_501']
        lawyer2 = users['lawyer_502']
        lawyer3 = users['lawyer_503']

        # --- Cases (fictional) ---
        cases_spec = [
            {
                'case_number': 'CIV/2024/118', 'cnr': 'GJ/AA/2024/000118', 'title': 'Sharma v. Agarwal Traders',
                'case_type': 'Civil', 'court': court1, 'room': room1, 'judge': judge1,
                'plaintiff': 'Rajesh Sharma', 'defendant': 'Agarwal Traders Pvt Ltd',
                'filed': today - timedelta(days=420), 'status': 'ACTIVE', 'priority': 'HIGH',
                'desc': 'Dispute over unpaid goods supplied; claim of INR 4,50,000.',
                'public': True, 'lawyer': lawyer1,
            },
            {
                'case_number': 'CRL/2024/032', 'cnr': 'GJ/AA/2024/000032', 'title': 'State v. Verma',
                'case_type': 'Criminal', 'court': court2, 'room': room3, 'judge': judge2,
                'plaintiff': 'State of Gujarat', 'defendant': 'Suresh Verma',
                'filed': today - timedelta(days=300), 'status': 'ADJOURNED', 'priority': 'URGENT',
                'desc': 'Criminal matter — evidence recording in progress.',
                'public': False, 'lawyer': lawyer2,
            },
            {
                'case_number': 'FAM/2023/245', 'cnr': 'GJ/AA/2023/000245', 'title': 'Khan v. Khan',
                'case_type': 'Family', 'court': court1, 'room': room2, 'judge': judge1,
                'plaintiff': 'Ayesha Khan', 'defendant': 'Imran Khan',
                'filed': today - timedelta(days=600), 'status': 'PENDING', 'priority': 'NORMAL',
                'desc': 'Family matter — settlement discussion ongoing.',
                'public': False, 'lawyer': lawyer3,
            },
            {
                'case_number': 'CIV/2023/401', 'cnr': 'GJ/AA/2023/000401', 'title': 'Patel v. Municipal Corp.',
                'case_type': 'Civil', 'court': court1, 'room': room1, 'judge': judge1,
                'plaintiff': 'Dinesh Patel', 'defendant': 'Ahmedabad Municipal Corporation',
                'filed': today - timedelta(days=700), 'status': 'RESERVED_FOR_ORDER', 'priority': 'NORMAL',
                'desc': 'Property tax dispute — judgment reserved.',
                'public': True, 'lawyer': lawyer1,
            },
            {
                'case_number': 'CIV/2020/077', 'cnr': 'GJ/AA/2020/000077', 'title': 'Desai v. Desai',
                'case_type': 'Civil', 'court': court2, 'room': room3, 'judge': judge2,
                'plaintiff': 'Hemant Desai', 'defendant': 'Gopal Desai',
                'filed': today - timedelta(days=1800), 'status': 'CLOSED', 'priority': 'LOW',
                'desc': 'Partition suit — disposed.',
                'public': False, 'lawyer': lawyer2,
            },
        ]

        cases = []
        for spec in cases_spec:
            case, created = Case.objects.get_or_create(
                case_number=spec['case_number'],
                defaults={
                    'cnr_number': spec['cnr'], 'title': spec['title'],
                    'description': spec['desc'], 'case_type': spec['case_type'],
                    'court': spec['court'], 'courtroom': spec['room'],
                    'filing_date': spec['filed'], 'status': spec['status'],
                    'priority': spec['priority'], 'plaintiff_name': spec['plaintiff'],
                    'defendant_name': spec['defendant'], 'assigned_judge': spec['judge'],
                    'judge_name': spec['judge'].get_full_name(),
                    'assigned_lawyer': spec['lawyer'],
                    'is_public': spec['public'], 'created_by': admin,
                },
            )
            if created:
                CaseEvent.objects.create(case=case, event_type='CASE_FILED',
                                         title=f'Case filed as {case.case_number}',
                                         event_date=case.filing_date, created_by=admin)
                CaseParty.objects.create(case=case, party_type='petitioner', name=spec['plaintiff'], is_public=spec['public'])
                CaseParty.objects.create(case=case, party_type='respondent', name=spec['defendant'], is_public=spec['public'])
                CaseLawyer.objects.create(case=case, lawyer=spec['lawyer'], role='lead', is_active=True)
            cases.append(case)
            self.stdout.write(f'  case {case.case_number} {"created" if created else "exists"}')

        # --- Hearings + proceedings (fictional) ---
        for i, case in enumerate(cases[:4]):
            for n in range(1, 4):
                h_date = case.filing_date + timedelta(days=90 * n)
                status = 'COMPLETED' if n < 3 else 'SCHEDULED'
                hearing, created = Hearing.objects.get_or_create(
                    case=case, hearing_number=n,
                    defaults={
                        'date': h_date, 'judge': case.assigned_judge,
                        'courtroom': case.courtroom, 'hearing_type': 'ARGUMENTS',
                        'purpose': 'Hearing for evidence and arguments',
                        'status': status, 'created_by': admin,
                    },
                )
                if created and status == 'COMPLETED':
                    HearingProceeding.objects.create(
                        hearing=hearing,
                        summary=f'Arguments heard; witnesses examined. Adjourned for further evidence.',
                        notes=f'Both counsels present. Next step: filing of evidence.',
                        directions='Parties to file remaining evidence within 14 days.',
                        recorded_by=judge1 if case.assigned_judge == judge1 else judge2,
                        next_hearing_date=h_date + timedelta(days=60),
                    )
                self.stdout.write(f'  hearing #{n} for {case.case_number} {"created" if created else "exists"}')

        # --- Orders (fictional) ---
        for case in cases[:4]:
            order, created = Order.objects.get_or_create(
                case=case, title=f'Order on interim application — {case.case_number}',
                defaults={
                    'order_type': 'INTERIM', 'summary': 'Interim order directing both parties to maintain status quo until next hearing.',
                    'date': today - timedelta(days=30), 'status': 'PUBLISHED',
                    'visibility': 'PUBLIC' if case.is_public else 'LAWYER_ONLY',
                    'is_public': case.is_public, 'created_by': case.assigned_judge,
                    'published_at': timezone.now() - timedelta(days=30),
                },
            )
            if created:
                OrderVersion.objects.create(order=order, version_number=1, content_text=order.summary,
                                            reason='Initial version', uploaded_by=case.assigned_judge)
                CaseEvent.objects.create(case=case, event_type='ORDER_PUBLISHED',
                                         title=f'Order published: {order.title}',
                                         event_date=today - timedelta(days=30), created_by=case.assigned_judge)

        # --- Documents (fictional, plain-text; pipeline will process) ---
        doc_specs = [
            ('CIV/2024/118', 'petition.txt', 'Petition', 'This is the original petition filed by Rajesh Sharma claiming INR 4,50,000 for unpaid goods supplied to Agarwal Traders.', 'LAWYER_ONLY'),
            ('CIV/2024/118', 'affidavit.txt', 'Affidavit', 'Affidavit of Rajesh Sharma sworn on the date of filing, attesting to the supply of goods and outstanding invoices.', 'LAWYER_ONLY'),
            ('CIV/2024/118', 'public-notice.txt', 'Annexure', 'Public notice regarding the pending civil dispute, published in the local gazette.', 'PUBLIC'),
            ('CRL/2024/032', 'evidence.txt', 'Evidence', 'Evidence recorded during the criminal matter including witness statements and forensic report summary.', 'JUDGE_ONLY'),
            ('FAM/2023/245', 'settlement-notes.txt', 'Other', 'Confidential settlement discussion notes between the parties.', 'LAWYER_ONLY'),
            ('CIV/2023/401', 'judgment-reserved.txt', 'Judgment', 'Matter reserved for judgment; written submissions received from both counsels.', 'LAWYER_ONLY'),
        ]
        for case_no, fname, dtype, content, vis in doc_specs:
            case = next((c for c in cases if c.case_number == case_no), None)
            if not case:
                continue
            if CaseDocument.objects.filter(file_name=fname, case=case).exists():
                continue
            doc = CaseDocument.objects.create(
                case=case, document_type=dtype.lower(), file_name=fname,
                file=SimpleUploadedFile(fname, content.encode(), content_type='text/plain'),
                file_size=len(content), mime_type='text/plain',
                uploaded_by=case.assigned_judge, description=f'Demo {dtype.lower()} document',
                visibility=vis,
            )
            # Run pipeline eagerly to create extraction + chunks
            from apps.documents.tasks import process_document_task
            process_document_task.run(str(doc.id))
            self.stdout.write(f'  document {fname} processed ({doc.processing_state})')

        # --- Tasks ---
        for case in cases[:3]:
            Task.objects.get_or_create(
                title=f'Review documents for {case.case_number}',
                defaults={
                    'description': 'Review newly filed documents and prepare submissions.',
                    'case': case, 'assigned_to': case.assigned_lawyer,
                    'created_by': case.assigned_judge, 'priority': 'NORMAL',
                    'status': 'TODO', 'due_date': today + timedelta(days=7),
                },
            )

        # --- Notifications ---
        for case in cases[:2]:
            Notification.objects.get_or_create(
                user=case.assigned_lawyer, notification_type='hearing_scheduled',
                title='Hearing Scheduled',
                defaults={
                    'message': f'Hearing scheduled for case {case.case_number}.',
                    'case': case, 'action_url': f'/cases/{case.id}',
                },
            )

        # --- Audit events ---
        AuditLog.objects.create(
            user=admin, action=AuditEventType.CSV_IMPORT, model_name='User',
            object_id='', changes={'note': 'Demo seed'}, ip_address='127.0.0.1',
            user_agent='seed-command', metadata={'source': 'seed_demo'},
        )

        self.stdout.write(self.style.SUCCESS(f'Demo data ready: {len(cases)} cases, '
                                             f'{Court.objects.count()} courts, {Hearing.objects.count()} hearings, '
                                             f'{CaseDocument.objects.count()} documents.'))
