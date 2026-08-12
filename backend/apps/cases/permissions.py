"""
Object/resource-level authorization service for the JCM platform.

The spec (§11, §34, §49) explicitly forbids `role == LAWYER` as the only
access check. Every sensitive endpoint must call these helpers, and the AI
retrieval pipeline must filter by case/document authorization BEFORE any
vector search.
"""
from django.db.models import Q

# ---------------------------------------------------------------------------
# Case-level authorization
# ---------------------------------------------------------------------------


def can_view_case(user, case) -> bool:
    """Can this user view this case?"""
    if not user or not user.is_authenticated:
        return bool(case and case.is_public)
    if user.role == 'admin':
        return True
    if user.role == 'guest':
        return bool(case and case.is_public)
    if user.role == 'judge':
        return (
            case.assigned_judge_id == user.id
            or case.created_by_id == user.id
        )
    # lawyer
    return (
        case.assigned_lawyer_id == user.id
        or case.assignments.filter(lawyer=user, is_active=True).exists()
        or case.case_lawyers.filter(lawyer=user, is_active=True).exists()
    )


def can_edit_case(user, case) -> bool:
    if not user or user.is_authenticated is False:
        return False
    if user.role == 'admin':
        return True
    if user.role == 'judge':
        return case.assigned_judge_id == user.id or case.created_by_id == user.id
    return False


def can_delete_case(user, case) -> bool:
    return bool(user and user.role == 'admin' and case)


def case_queryset_for(user):
    """Base queryset of cases the user is authorized to see."""
    from .models import Case
    if not user or not user.is_authenticated:
        return Case.objects.filter(is_public=True)
    if user.role == 'admin':
        return Case.objects.all()
    if user.role == 'guest':
        return Case.objects.filter(is_public=True)
    if user.role == 'judge':
        return Case.objects.filter(
            Q(assigned_judge=user) | Q(created_by=user)
        ).distinct()
    # lawyer
    return Case.objects.filter(
        Q(assigned_lawyer=user)
        | Q(assignments__lawyer=user, assignments__is_active=True)
        | Q(case_lawyers__lawyer=user, case_lawyers__is_active=True)
    ).distinct()


# ---------------------------------------------------------------------------
# Document-level authorization
# ---------------------------------------------------------------------------

DOC_VISIBILITY_RANK = {
    'PUBLIC': 0,
    'LAWYER_ONLY': 1,
    'JUDGE_ONLY': 2,
    'RESTRICTED': 3,
    'ADMIN_ONLY': 4,
}


def can_view_document(user, document) -> bool:
    """Can this user view/download this document?"""
    if not user or not user.is_authenticated:
        return bool(document and document.visibility == 'PUBLIC')
    if not document:
        return False

    # Admin is NOT automatically granted all sensitive content (§19).
    # Explicit grants + PUBLIC + own uploads.
    if user.role == 'admin' and document.visibility in ('PUBLIC', 'ADMIN_ONLY'):
        return True
    if user.role == 'admin' and document.uploaded_by_id == user.id:
        return True

    if document.visibility == 'PUBLIC':
        return True

    # Explicit grant overrides visibility for the granted user.
    if document.access_grants.filter(user=user, access_level__in=['read', 'download', 'write']).exists():
        return True

    if not can_view_case(user, document.case):
        return False

    if document.visibility == 'LAWYER_ONLY':
        return user.role in ('judge', 'lawyer', 'admin')
    if document.visibility == 'JUDGE_ONLY':
        return user.role in ('judge', 'admin')
    if document.visibility == 'RESTRICTED':
        # Restricted: only explicit grants (checked above) or admin/judge of the case
        return user.role == 'admin' or (
            user.role == 'judge' and document.case.assigned_judge_id == user.id
        )
    if document.visibility == 'ADMIN_ONLY':
        return user.role == 'admin'
    return False


def can_download_document(user, document) -> bool:
    if not can_view_document(user, document):
        return False
    if not user or not user.is_authenticated:
        return document.visibility == 'PUBLIC'
    # Explicit download grant
    if document.access_grants.filter(user=user, access_level='download').exists():
        return True
    return True  # view implies download for authorized users


def document_queryset_for(user):
    """Base queryset of documents the user is authorized to see."""
    from apps.documents.models import CaseDocument
    if not user or not user.is_authenticated:
        return CaseDocument.objects.filter(visibility='PUBLIC', state='ACTIVE')
    if user.role == 'admin':
        return CaseDocument.objects.filter(
            Q(visibility__in=['PUBLIC', 'ADMIN_ONLY']) | Q(uploaded_by=user)
        )
    if user.role == 'guest':
        return CaseDocument.objects.filter(visibility='PUBLIC', state='ACTIVE')
    if user.role == 'judge':
        case_ids = case_queryset_for(user).values_list('id', flat=True)
        return CaseDocument.objects.filter(
            Q(case_id__in=case_ids)
            & Q(visibility__in=['PUBLIC', 'LAWYER_ONLY', 'JUDGE_ONLY'])
        ) | CaseDocument.objects.filter(uploaded_by=user)
    # lawyer
    case_ids = case_queryset_for(user).values_list('id', flat=True)
    return CaseDocument.objects.filter(
        Q(case_id__in=case_ids) & Q(visibility__in=['PUBLIC', 'LAWYER_ONLY'])
    ) | CaseDocument.objects.filter(
        access_grants__user=user
    ) | CaseDocument.objects.filter(uploaded_by=user)


# ---------------------------------------------------------------------------
# Hearing / Order / Task authorization
# ---------------------------------------------------------------------------


def can_view_hearing(user, hearing) -> bool:
    if not user or not user.is_authenticated:
        return bool(hearing and hearing.is_public)
    if user.role == 'admin':
        return True
    if user.role == 'guest':
        return bool(hearing and hearing.is_public)
    return can_view_case(user, hearing.case)


def can_edit_hearing(user, hearing) -> bool:
    if not user or user.is_authenticated is False:
        return False
    if user.role == 'admin':
        return True
    if user.role == 'judge':
        case = hearing.case
        return case.assigned_judge_id == user.id or case.created_by_id == user.id
    return False


def can_view_order(user, order) -> bool:
    if not user or not user.is_authenticated:
        return bool(order and order.is_public and order.status == 'PUBLISHED')
    if user.role == 'admin':
        return True
    if user.role == 'guest':
        return bool(order and order.is_public and order.status == 'PUBLISHED')
    if order.status == 'DRAFT' and user.role != 'judge':
        return False
    return can_view_case(user, order.case)


def can_view_proceeding(user, proceeding) -> bool:
    if not user or not user.is_authenticated:
        return bool(proceeding and proceeding.is_public)
    if user.role == 'admin':
        return True
    if user.role == 'guest':
        return bool(proceeding and proceeding.is_public)
    return can_view_case(user, proceeding.hearing.case)


def can_view_task(user, task) -> bool:
    if not user or not user.is_authenticated:
        return False
    if user.role == 'admin':
        return True
    return task.assigned_to_id == user.id or task.created_by_id == user.id


def task_queryset_for(user):
    """Tasks visible to a user."""
    from apps.tasks.models import Task
    if not user or not user.is_authenticated:
        return Task.objects.none()
    if user.role == 'admin':
        return Task.objects.all()
    return Task.objects.filter(Q(assigned_to=user) | Q(created_by=user)).distinct()
