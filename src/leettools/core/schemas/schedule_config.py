from typing import List, Optional

from pydantic import BaseModel

from leettools.common.utils.obj_utils import add_fieldname_constants
from leettools.core.consts.schedule_type import ScheduleType


@add_fieldname_constants
class ScheduleConfig(BaseModel):
    schedule_type: ScheduleType = ScheduleType.ONCE

    # different schedule types may use different fields
    # for example, for daily schedule, we may only use
    # schedule_utc_minutes_of_day, which means we only run
    # the job at a specific time of the day.
    schedule_utc_minutes_of_day: Optional[int] = None
    schedule_interval_minutes: Optional[int] = None
    schedule_days_of_week: Optional[List[int]] = None
    schedule_days_of_month: Optional[List[int]] = None
