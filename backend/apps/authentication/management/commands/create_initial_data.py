from django.core.management.base import BaseCommand
from django.utils import timezone


class Command(BaseCommand):
    help = 'Create initial admin, lawyer, sample case, timeline, and notifications for development'

    def handle(self, *args, **options):
        from apps.authentication.models import User
        from apps.cases.models import Case, CaseEvent, CaseAssignment
        from apps.notifications.models import Notification

        now = timezone.now()

        seed_users = [
            {
                'email': 'admin@example.com',
                'password': 'Aagam%1234',
                'role': 'admin',
                'first_name': 'Admin',
                'last_name': 'User',
                'professional_id': 'ADM-001',
                'is_staff': True,
                'is_superuser': True,
            },
            {
                'email': 'aagam0312@gmail.com',
                'password': 'Aagam%1234',
                'role': 'lawyer',
                'first_name': 'Aagam',
                'last_name': 'Lawyer',
                'professional_id': 'LAW-001',
                'is_staff': False,
                'is_superuser': False,
            },
            {
                'email': 'pass.iloveben10@gmail.com',
                'password': 'Aagam%1234',
                'role': 'judge',
                'first_name': 'Aagam',
                'last_name': 'Judge',
                'professional_id': 'JDG-001',
                'is_staff': False,
                'is_superuser': False,
            },
        ]
        seed_emails = [item['email'] for item in seed_users]
        User.objects.exclude(email__in=seed_emails).delete()

        users_by_role = {}
        for item in seed_users:
            user, _ = User.objects.update_or_create(
                email=item['email'],
                defaults={
                    'username': item['email'],
                    'first_name': item['first_name'],
                    'last_name': item['last_name'],
                    'role': item['role'],
                    'professional_id': item['professional_id'],
                    'is_staff': item['is_staff'],
                    'is_superuser': item['is_superuser'],
                    'is_active': True,
                    'is_verified': True,
                },
            )
            user.set_password(item['password'])
            user.save(update_fields=['password'])
            users_by_role[item['role']] = user
            self.stdout.write(self.style.SUCCESS(f"Ready {item['role']} user: {item['email']}"))

        admin = users_by_role['admin']
        lawyer = users_by_role['lawyer']
        judge = users_by_role['judge']

        # Create a sample case
        case_number = '2025-ABC-101'
        if not Case.objects.filter(case_number=case_number).exists():
            case = Case.objects.create(
                case_number=case_number,
                title='Smith v. Doe',
                description='Sample case created for development and testing purposes.',
                court_name='District Court',
                case_type='Civil',
                filing_date=now.date(),
                next_hearing_date=(now + timezone.timedelta(days=30)).date(),
                status='active',
                plaintiff_name='John Smith',
                defendant_name='Jane Doe',
                created_by=admin,
                assigned_judge=judge,
                judge_name=judge.get_full_name(),
                assigned_lawyer=lawyer
            )
            self.stdout.write(self.style.SUCCESS(f'Created sample case: {case_number}'))
        else:
            case = Case.objects.get(case_number=case_number)
            self.stdout.write(f'Sample case already exists: {case_number}')

        # Add a timeline event
        if not CaseEvent.objects.filter(case=case, event_type='CASE_FILED').exists():
            evt = CaseEvent.objects.create(
                case=case,
                event_type='CASE_FILED',
                title='Case filed with initial petition',
                description='Case filed with initial petition',
                event_date=now.date(),
                created_by=admin
            )
            self.stdout.write(self.style.SUCCESS('Created timeline event: filing'))
        else:
            self.stdout.write('Timeline event filing already exists')

        # Assign lawyer
        if not CaseAssignment.objects.filter(case=case, lawyer=lawyer).exists():
            asg = CaseAssignment.objects.create(
                case=case,
                lawyer=lawyer,
                role='primary'
            )
            self.stdout.write(self.style.SUCCESS('Assigned lawyer to case'))
        else:
            self.stdout.write('Lawyer already assigned to case')

        # Create a notification for the lawyer
        Notification.objects.create(
            user=lawyer,
            notification_type='case_assigned',
            title='New Case Assigned',
            message=f'You have been assigned to case {case.case_number}',
            case=case
        )
        self.stdout.write(self.style.SUCCESS('Created notification for lawyer'))

        self.stdout.write(self.style.SUCCESS('Initial data setup complete'))
