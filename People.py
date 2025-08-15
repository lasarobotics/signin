from __future__ import annotations
from typing import List


class PersonRecord:
    def __init__(self, raw_record: List[str], row_number: int) -> None:
        self.row_number = row_number
        self.id = ''
        self.last_name = ''
        self.first_name = ''
        self.graduation_year = ''
        self.roster_status = ''
        self.school_email = ''
        self.personal_email = ''
        self.role = ''
        self.slack_id = ''
        try:
            self.id = raw_record[0]
            self.last_name = raw_record[1]
            self.first_name = raw_record[2]
            self.graduation_year = raw_record[3]
            self.roster_status = raw_record[4]
            self.school_email = raw_record[5]
            self.personal_email = raw_record[6]
            self.role = raw_record[7]
            self.slack_id = raw_record[8]
        except IndexError:
            pass
            # print(f'Unexpected Person Record format: {raw_record}')

    def get_raw_record(self) -> List[str]:
        return [
            self.id,
            self.last_name,
            self.first_name,
            self.graduation_year,
            self.roster_status,
            self.school_email,
            self.personal_email,
            self.role,
            self.slack_id,
        ]

    def __str__(self) -> str:
        if self.roster_status == 'On Roster':
            return f'{self.id}:{self.row_number} - {self.first_name} {self.last_name}, {self.graduation_year}, {self.roster_status}, {self.school_email}, {self.personal_email}, {self.role}'
        else:
            return f'{self.id}:{self.row_number} - {self.first_name} {self.last_name}, {self.graduation_year}, {self.roster_status}'

    def __repr__(self) -> str:
        return self.__str__()

    def __eq__(self, other: PersonRecord) -> bool:
        return self.id == other.id
