from api.models.job_base import JobStatus
from services.domain.job_base import JobStatus as DomainJobStatus

_STATUS_MAP: dict[DomainJobStatus, JobStatus] = {
    DomainJobStatus.PENDING: JobStatus.PENDING,
    DomainJobStatus.RUNNING: JobStatus.RUNNING,
    DomainJobStatus.DONE: JobStatus.DONE,
    DomainJobStatus.FAILED: JobStatus.FAILED,
}


def map_status(status: DomainJobStatus) -> JobStatus:
    return _STATUS_MAP[status]
