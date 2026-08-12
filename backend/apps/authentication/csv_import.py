"""
Admin CSV import services (spec §12, §64).

Flow: upload → parse → validate → preview → confirm → import → report.
Staff import (judges/lawyers) and case import are both supported.
No unvalidated data ever reaches the database — the admin must confirm
after reviewing a preview with row-level errors.
"""
import csv
import io
import logging
from datetime import datetime, date

from django.contrib.auth.models import User as AuthUser  # noqa
from apps.authentication.models import User

logger = logging.getLogger(__name__)


class CSVParseResult:
    def __init__(self):
        self.rows = []          # list of dicts (validated data)
        self.errors = []        # list of {row, field, message}
        self.headers = []
        self.total_rows = 0

    @property
    def valid_count(self):
        return len(self.rows)

    @property
    def error_count(self):
        return len(self.errors)


def parse_csv(file_obj):
    """Read CSV bytes → list of dict rows."""
    text = file_obj.read().decode('utf-8-sig')
    reader = csv.DictReader(io.StringIO(text))
    rows = list(reader)
    return reader.fieldnames or [], rows


# ---------------------------------------------------------------------------
# Staff (judge/lawyer) import
# ---------------------------------------------------------------------------

STAFF_EXPECTED = {'email', 'first_name', 'last_name'}
STAFF_OPTIONAL = {'id', 'professional_id', 'unique_id', 'username', 'name', 'password', 'phone_number'}


def validate_staff_row(row, index, role):
    errors = []
    email = (row.get('email') or '').strip().lower()
    first_name = (row.get('first_name') or row.get('name') or '').strip()
    last_name = (row.get('last_name') or '').strip()
    professional_id = (row.get('professional_id') or row.get('id') or row.get('unique_id') or '').strip()

    if not email or '@' not in email:
        errors.append({'row': index, 'field': 'email', 'message': 'Valid email is required'})
    if not first_name:
        errors.append({'row': index, 'field': 'first_name', 'message': 'First name is required'})
    if not professional_id:
        errors.append({'row': index, 'field': 'professional_id', 'message': 'Professional ID is required'})

    return {
        'row': index,
        'data': {
            'email': email,
            'username': (row.get('username') or email or f"user{index}").strip(),
            'first_name': first_name,
            'last_name': last_name,
            'role': role,
            'professional_id': professional_id or None,
            'phone_number': (row.get('phone_number') or '').strip() or None,
            'password': (row.get('password') or '').strip(),
        },
        'errors': errors,
    }


def preview_staff_csv(file_obj, role):
    headers, rows = parse_csv(file_obj)
    result = CSVParseResult()
    result.headers = headers
    result.total_rows = len(rows)

    for i, row in enumerate(rows, start=2):  # row 1 = header
        parsed = validate_staff_row(row, i, role)
        if parsed['errors']:
            result.errors.extend(parsed['errors'])
        else:
            # duplicate detection within file + against DB
            dup_msg = _staff_duplicate_check(parsed['data'])
            if dup_msg:
                result.errors.append({'row': i, 'field': 'email', 'message': dup_msg})
            else:
                result.rows.append(parsed['data'])
    return result


def _staff_duplicate_check(data):
    if User.objects.filter(email=data['email']).exists():
        return f"Email {data['email']} already exists"
    if data.get('professional_id') and User.objects.filter(professional_id=data['professional_id']).exists():
        return f"Professional ID {data['professional_id']} already exists"
    return ''


def import_staff_rows(rows, role, actor):
    """Import validated staff rows. Returns (created, updated, report_rows)."""
    created = 0
    report = []
    for data in rows:
        user, was_created = User.objects.update_or_create(
            email=data['email'],
            defaults={
                'username': data['username'],
                'first_name': data['first_name'],
                'last_name': data['last_name'],
                'role': role,
                'professional_id': data['professional_id'],
                'phone_number': data.get('phone_number'),
                'is_verified': True,
                'is_active': True,
            },
        )
        if data.get('password'):
            user.set_password(data['password'])
            user.save(update_fields=['password'])
        elif was_created:
            user.set_unusable_password()
            user.save(update_fields=['password'])
        if was_created:
            created += 1
        report.append({'email': user.email, 'professional_id': user.professional_id, 'status': 'created' if was_created else 'updated'})
    return created, report


# ---------------------------------------------------------------------------
# Case import
# ---------------------------------------------------------------------------

CASE_FIELDS = ['case_number', 'cnr_number', 'title', 'case_type', 'court_name',
               'filing_date', 'registration_date', 'status', 'priority',
               'plaintiff_name', 'defendant_name', 'description', 'judge_email',
               'lawyer_email', 'subject', 'category', 'is_public']

STATUS_VALUES = ['FILED', 'REGISTERED', 'PENDING', 'ACTIVE', 'ADJOURNED',
                 'RESERVED_FOR_ORDER', 'DISPOSED', 'TRANSFERRED', 'CLOSED']
PRIORITY_VALUES = ['URGENT', 'HIGH', 'NORMAL', 'LOW']


def validate_case_row(row, index):
    from apps.cases.models import Case
    errors = []
    case_number = (row.get('case_number') or '').strip()
    title = (row.get('title') or '').strip()
    case_type = (row.get('case_type') or '').strip()
    filing_date = (row.get('filing_date') or '').strip()

    if not case_number:
        errors.append({'row': index, 'field': 'case_number', 'message': 'Case number is required'})
    elif Case.objects.filter(case_number=case_number).exists():
        errors.append({'row': index, 'field': 'case_number', 'message': f'Case {case_number} already exists'})
    if not title:
        errors.append({'row': index, 'field': 'title', 'message': 'Title is required'})
    if not case_type:
        errors.append({'row': index, 'field': 'case_type', 'message': 'Case type is required'})

    filing_date_obj = None
    if filing_date:
        try:
            filing_date_obj = date.fromisoformat(filing_date)
        except ValueError:
            errors.append({'row': index, 'field': 'filing_date', 'message': 'Invalid date (use YYYY-MM-DD)'})

    status_val = (row.get('status') or 'PENDING').upper()
    if status_val not in STATUS_VALUES:
        errors.append({'row': index, 'field': 'status', 'message': f'Invalid status: {status_val}'})
        status_val = 'PENDING'

    priority = (row.get('priority') or 'NORMAL').upper()
    if priority not in PRIORITY_VALUES:
        errors.append({'row': index, 'field': 'priority', 'message': f'Invalid priority: {priority}'})
        priority = 'NORMAL'

    # Resolve judge/lawyer by email
    judge_email = (row.get('judge_email') or '').strip().lower()
    lawyer_email = (row.get('lawyer_email') or '').strip().lower()
    judge = User.objects.filter(email=judge_email, role='judge').first() if judge_email else None
    lawyer = User.objects.filter(email=lawyer_email, role='lawyer').first() if lawyer_email else None
    if judge_email and not judge:
        errors.append({'row': index, 'field': 'judge_email', 'message': f'No judge found: {judge_email}'})
    if lawyer_email and not lawyer:
        errors.append({'row': index, 'field': 'lawyer_email', 'message': f'No lawyer found: {lawyer_email}'})

    data = {
        'case_number': case_number,
        'cnr_number': (row.get('cnr_number') or '').strip() or None,
        'title': title,
        'description': (row.get('description') or '').strip(),
        'case_type': case_type,
        'court_name': (row.get('court_name') or '').strip(),
        'filing_date': filing_date_obj,
        'registration_date': _parse_date(row.get('registration_date')),
        'status': status_val,
        'priority': priority,
        'plaintiff_name': (row.get('plaintiff_name') or '').strip(),
        'defendant_name': (row.get('defendant_name') or '').strip(),
        'assigned_judge': judge,
        'assigned_lawyer': lawyer,
        'judge_name': judge.get_full_name() if judge else (row.get('judge_email') or '').strip(),
        'subject': (row.get('subject') or '').strip(),
        'category': (row.get('category') or '').strip(),
        'is_public': (row.get('is_public') or '').strip().lower() in ('1', 'true', 'yes', 'public'),
    }
    return {'row': index, 'data': data, 'errors': errors}


def _parse_date(value):
    value = (value or '').strip()
    if not value:
        return None
    try:
        return date.fromisoformat(value)
    except ValueError:
        return None


def preview_case_csv(file_obj):
    headers, rows = parse_csv(file_obj)
    result = CSVParseResult()
    result.headers = headers
    result.total_rows = len(rows)
    for i, row in enumerate(rows, start=2):
        parsed = validate_case_row(row, i)
        if parsed['errors']:
            result.errors.extend(parsed['errors'])
        else:
            result.rows.append(parsed['data'])
    return result


def import_case_rows(rows, actor):
    from apps.cases.models import Case, CaseEvent
    from apps.cases.models import CaseStatus
    created = 0
    report = []
    for data in rows:
        case = Case.objects.create(
            **{k: v for k, v in data.items() if k != 'assigned_judge'},
            assigned_judge=data.get('assigned_judge'),
            created_by=actor,
        )
        CaseEvent.objects.create(
            case=case,
            event_type='CASE_FILED',
            title=f"Case filed as {case.case_number} (CSV import)",
            event_date=case.filing_date or date.today(),
            created_by=actor,
        )
        created += 1
        report.append({'case_number': case.case_number, 'status': case.status})
    return created, report
