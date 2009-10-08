"""Django-future -- scheduled jobs in Django."""

import datetime
from django_future.models import ScheduledJob


__all__ = ['schedule_job']


def schedule_job(date, callable_name, content_object=None, expires='7d',
                 args=(), kwargs={}):
    """Schedule a job.

    `date` may be a datetime.datetime or a datetime.timedelta.

    The callable to be executed may be specified in two ways:
     - set `callable_name` to an identifier ('mypackage.myapp.some_function').
     - specify an instance of a model as content_object and set
       `callable_name` to a method name ('do_job')

    The scheduler will not attempt to run the job if its expiration date has
    passed.

    """
    assert callable_name and isinstance(callable_name, str), callable_name
    if isinstance(date, basestring):
        date = _parse_timedelta(date)
    if isinstance(date, datetime.timedelta):
        date = datetime.datetime.now() + date
    job = ScheduledJob(callable_name=callable_name, time_slot_start=date)
    if expires:
        if isinstance(expires, basestring):
            expires = _parse_timedelta(expires)
        if isinstance(expires, datetime.timedelta):
            expires = date + expires
        job.time_slot_end = expires
    if content_object:
        job.content_object = content_object
    job.args = args
    job.kwargs = kwargs
    job.save()


_TIMEDELTA_SUFFIXES = {'m': 'minutes',
                       'h': 'hours',
                       'd': 'days',
                       'w': 'weeks}

def _parse_timedelta(s):
    n, suffix = int(s[:-1]), s[-1]
    key = _TIMEDELTA_SUFFIXES[suffix]
    kwargs = {key: n}
    return datetime.timedelta(**kwargs)


def run_jobs():
    """Run scheduled jobs."""
    # TODO: locking; make sure that several instances of ``run_jobs`` are not
    # running concurrently.
    now = datetime.datetime.now()
    jobs = ScheduledJob.objects.filter(status='scheduled',
                                       time_slot_start__lte=now,
                                       time_slot_end__gt=now)
    for job in jobs:
        # TODO: transactions
        job.status = 'active'
        job.save()
        try:
            job.run()
        except Exception:
            # TODO: Report problem; log?
            # TODO: transactions
            job.status = 'failed'
            job.save()
            raise
        else:
            job.status = 'complete'
            job.save()