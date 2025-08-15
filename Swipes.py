from __future__ import annotations

from datetime import datetime
from typing import List


class SwipeRecord:
    def __init__(self, raw_record: List[str], row_number: int) -> None:
        self.row_number = row_number
        self.swipe_time = ''
        self.person_id = ''
        try:
            self.swipe_time = raw_record[0]
            self.person_id = raw_record[1]
        except IndexError:
            pass
            # print(f'Unexpected Swipe Record format: {raw_record}')
        self.swipe_time_dt = datetime.strptime(self.swipe_time, '%m/%d/%Y %H:%M:%S')

    def get_raw_record(self) -> List[str]:
        return [
            self.swipe_time,
            self.person_id
        ]

    def __str__(self) -> str:
        return f'{self.row_number} - {self.swipe_time} {self.person_id}'

    def __repr__(self) -> str:
        return self.__str__()

    def __eq__(self, other: SwipeRecord) -> bool:
        return self.swipe_time == other.swipe_time and self.person_id == other.person_id
