from __future__ import annotations

from datetime import datetime, timedelta
from typing import List


class AttendanceRecord:
    def __init__(self, raw_record: List[str], row_number: int) -> None:
        self.row_number = row_number
        self.sign_in_time = ''
        self.sign_out_time = ''
        self.person_id = ''
        try:
            self.sign_in_time = raw_record[0]
            self.sign_out_time = raw_record[1]
            self.person_id = raw_record[2]
        except IndexError:
            pass
            # print(f'Unexpected Swipe Record format: {raw_record}')
        self.sign_in_time_dt = datetime.strptime(self.sign_in_time, '%m/%d/%Y %H:%M:%S')
        self.sign_out_time_dt = None
        self.total_time = timedelta()
        try:
            self.sign_out_time_dt = datetime.strptime(self.sign_out_time, '%m/%d/%Y %H:%M:%S')
            self.total_time = self.sign_out_time_dt - self.sign_in_time_dt
        except ValueError:
            pass

    def get_raw_record(self) -> List[str]:
        return [
            self.sign_in_time,
            self.sign_out_time,
            self.person_id
        ]

    def __str__(self) -> str:
        return f'{self.row_number} - {self.sign_in_time} -> {self.sign_out_time} {self.person_id}'

    def __repr__(self) -> str:
        return self.__str__()
